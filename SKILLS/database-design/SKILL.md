---
name: Database Design
description: Schema design, normalization, indexing strategy, ORM selection, and migration best practices for relational databases
phase: 2
---

# Database Design

## Normalization Rules

Normalization eliminates redundancy and ensures data integrity. Apply these forms sequentially.

### First Normal Form (1NF)
- Each column contains atomic (indivisible) values.
- No repeating groups or arrays stored in a single column.
- Each row is unique (has a primary key).

**Violation**: A `tags` column containing `"react,typescript,nextjs"`.
**Fix**: Create a separate `tags` table and a join table `post_tags`.

### Second Normal Form (2NF)
- Satisfies 1NF.
- Every non-key column depends on the entire primary key, not just part of it.
- Relevant when using composite primary keys.

**Violation**: A table `(order_id, product_id, product_name, quantity)` where `product_name` depends only on `product_id`.
**Fix**: Move `product_name` to a `products` table.

### Third Normal Form (3NF)
- Satisfies 2NF.
- No non-key column depends on another non-key column (no transitive dependencies).

**Violation**: A table `(employee_id, department_id, department_name)` where `department_name` depends on `department_id`, not on `employee_id`.
**Fix**: Move `department_name` to a `departments` table.

### When to Denormalize

Denormalization is a deliberate tradeoff: storage and write complexity for read performance.

- **Read-heavy dashboards**: Materialized views or precomputed summary tables.
- **Avoiding expensive joins**: Storing a `user_name` alongside `user_id` in a `comments` table when you always display both.
- **Counters and aggregates**: A `follower_count` column on `profiles` instead of counting the `followers` table every read.
- **Event logs and audit trails**: These are append-only and naturally denormalized.

Always document why you denormalized. Add a comment in the migration.

## Index Strategy

### When to Create Indexes
- Columns used in `WHERE` clauses frequently.
- Columns used in `JOIN` conditions.
- Columns used in `ORDER BY` with `LIMIT` (pagination).
- Foreign key columns (PostgreSQL does not auto-index these).

### When NOT to Index
- Small tables (under a few thousand rows). Sequential scan is faster.
- Columns with very low cardinality (e.g., a boolean `is_active` with 50/50 distribution).
- Write-heavy tables where index maintenance cost outweighs read benefit.

### Index Types in PostgreSQL
- **B-tree** (default): Equality and range queries. Use for most cases.
- **GIN**: Full-text search, JSONB containment, array operations.
- **GiST**: Geometric data, range types, full-text search (alternative to GIN).
- **BRIN**: Very large tables with naturally ordered data (e.g., timestamp columns on append-only tables).

### Composite Indexes
Column order matters. A composite index on `(tenant_id, created_at)` supports queries filtering by `tenant_id` alone or by `tenant_id AND created_at`, but NOT by `created_at` alone. Place the most selective column first.

### Partial Indexes
Index only a subset of rows. Useful for queries that always include a condition:
```sql
CREATE INDEX idx_active_users ON users (email) WHERE is_active = true;
```

## Common Schema Patterns

### Polymorphic Associations
A single table references different parent tables.

**Approach A -- Separate foreign keys**:
```sql
-- comments table
commentable_type TEXT NOT NULL,  -- 'post' or 'video'
post_id UUID REFERENCES posts(id),
video_id UUID REFERENCES videos(id),
CHECK (
  (commentable_type = 'post' AND post_id IS NOT NULL AND video_id IS NULL) OR
  (commentable_type = 'video' AND video_id IS NOT NULL AND post_id IS NULL)
)
```

**Approach B -- Shared interface table** (preferred for complex cases):
Create a `commentable_items` table that all commentable entities reference via a shared ID.

### Entity-Attribute-Value (EAV)
Stores arbitrary key-value pairs for an entity. Flexible but hard to query and validate.
```sql
entity_id UUID, attribute_name TEXT, attribute_value TEXT
```
**Use sparingly**. Prefer JSONB columns in PostgreSQL for semi-structured data -- you get indexing (GIN) and validation (check constraints) without the query complexity of EAV.

### Adjacency List (Tree Structures)
Each row has a `parent_id` referencing another row in the same table.
```sql
id UUID PRIMARY KEY,
name TEXT NOT NULL,
parent_id UUID REFERENCES categories(id)
```
Simple to implement. Recursive queries (`WITH RECURSIVE`) handle tree traversal. For very deep or frequently queried trees, consider **materialized path** (`path TEXT` like `/1/4/12/`) or **closure table** patterns.

### Soft Deletes
Add a `deleted_at TIMESTAMPTZ` column instead of actually deleting rows. Filter with `WHERE deleted_at IS NULL` in all queries. Create a partial index on frequently queried columns that excludes soft-deleted rows.

## ORM Comparison

| Feature | Prisma | Drizzle | TypeORM |
|---|---|---|---|
| Type safety | Excellent (generated client) | Excellent (schema-first TS) | Moderate (decorators, runtime types) |
| Schema definition | `schema.prisma` DSL | TypeScript files | TypeScript decorators or YAML |
| Migration approach | Auto-generated from schema diff | SQL-based or push | Auto-generated or manual SQL |
| Raw SQL support | `$queryRaw` and `$executeRaw` | First-class SQL builder | Query builder and raw SQL |
| Performance | Good, some overhead from client | Minimal overhead, close to raw SQL | Higher overhead, complex query generation |
| Learning curve | Low -- declarative schema is intuitive | Medium -- requires SQL knowledge | Medium -- decorator-heavy, many concepts |
| Edge/serverless | Supported (with adapter) | Excellent (lightweight) | Poor (heavy initialization) |
| Community/ecosystem | Large, well-funded, extensive docs | Growing rapidly, modern approach | Mature but less actively developed |

### Recommendation
- **Prisma**: Best for teams that want a batteries-included experience with excellent DX and documentation. Watch for N+1 queries.
- **Drizzle**: Best for teams that want type safety with full SQL control and minimal runtime overhead. Ideal for edge and serverless.
- **TypeORM**: Consider only for existing projects already using it. Not recommended for new projects due to maintenance pace and runtime weight.

## Migration Best Practices

### General Rules
1. Every schema change goes through a migration. Never modify the database manually in production.
2. Migrations must be idempotent where possible. Use `IF NOT EXISTS`, `IF EXISTS` guards.
3. Migrations must be reversible. Always write a corresponding down migration or document why rollback is not possible.
4. Never modify a migration that has already been applied to production. Create a new migration instead.
5. Name migrations descriptively: `add_stripe_customer_id_to_profiles`, not `update_table`.

### Safe Migration Practices for PostgreSQL
- **Adding a column**: Safe. Use `DEFAULT` only if you accept a table rewrite (small table) or use `ALTER COLUMN SET DEFAULT` separately.
- **Adding an index**: Use `CREATE INDEX CONCURRENTLY` to avoid locking the table.
- **Renaming a column**: Dangerous in production. Deploy in phases -- add new column, backfill, update code, drop old column.
- **Dropping a column**: First remove all code references, deploy, then drop the column in a subsequent migration.
- **Changing a column type**: Often requires a table rewrite. Prefer adding a new column and migrating data.

### Migration Workflow
1. Develop and test migrations locally.
2. Apply to a staging environment that mirrors production schema.
3. Review the migration SQL in code review -- treat it as production code.
4. Apply to production during low-traffic windows for large data migrations.
5. Monitor query performance after applying (check for missing indexes, slow queries).

### Data Migrations
Keep schema migrations and data migrations separate. Schema changes should not include business logic for transforming data. Write data migrations as standalone scripts that can be re-run safely.
