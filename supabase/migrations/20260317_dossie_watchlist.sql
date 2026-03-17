-- Tabela para gerir os temas do dossiê via Telegram (/watchlist)
-- Substitui o WATCHLIST hardcoded em dossie.py (mantido como fallback)

CREATE TABLE IF NOT EXISTS dossie_watchlist (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    nome        text NOT NULL,
    area        text NOT NULL DEFAULT 'mundo',
    prioridade  text NOT NULL DEFAULT 'p2',
    enabled     boolean NOT NULL DEFAULT true,
    queries     text[] NOT NULL DEFAULT '{}',
    created_at  timestamptz DEFAULT now(),
    updated_at  timestamptz DEFAULT now()
);

-- Migrar os temas actuais do dossie.py para a DB
INSERT INTO dossie_watchlist (nome, area, prioridade, queries) VALUES
(
    'Cuba — Colapso do Regime',
    'geopolitica', 'p1',
    ARRAY[
        'Cuba power outages economic collapse 2026',
        'Cuba protests regime opposition 2026',
        'Cuba food shortage hunger crisis 2026'
    ]
),
(
    'Irão — Regime, Terrorismo e Direitos Humanos',
    'geopolitica', 'p1',
    ARRAY[
        'Iran executions death penalty 2026 statistics',
        'Iran FATF terrorism financing sanctions',
        'Iran protests women rights 2026'
    ]
),
(
    'Argentina — Resultados Económicos Milei',
    'economia', 'p2',
    ARRAY[
        'Argentina inflation rate 2026 Milei results data',
        'Argentina GDP growth economy Milei 2026',
        'Argentina poverty rate reduction 2026'
    ]
),
(
    'El Salvador — Segurança e Modelo Bukele',
    'geopolitica', 'p2',
    ARRAY[
        'El Salvador homicide rate 2026 statistics',
        'El Salvador economy GDP growth Bukele 2026',
        'El Salvador Bitcoin results 2026'
    ]
),
(
    'Corrupção — Casos e Relatórios',
    'justica', 'p2',
    ARRAY[
        'Transparency International corruption index 2026',
        'EU corruption cases 2026 government officials',
        'Portugal corruption casos 2026'
    ]
);
