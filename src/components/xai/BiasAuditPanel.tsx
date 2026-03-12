import type { Source } from "@/types/source";

interface BiasAuditPanelProps {
  sources: Array<{
    source: Source;
    supports: boolean;
  }>;
}

export function BiasAuditPanel({ sources }: BiasAuditPanelProps) {
  if (!sources || sources.length === 0) return null;

  const supportCount = sources.filter((s) => s.supports).length;
  const contradictCount = sources.length - supportCount;
  const supportPct = Math.round((supportCount / sources.length) * 100);
  const contradictPct = 100 - supportPct;

  // Source type diversity
  const sourceTypes = new Set(sources.map((s) => s.source.source_type));
  const domainCount = new Set(sources.map((s) => s.source.domain)).size;

  // Reliability distribution
  const reliableCount = sources.filter(
    (s) => (s.source.reliability_score || 0) >= 0.7,
  ).length;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
        Auditoria de Vies
      </h3>

      {/* Support vs Contradict */}
      <div className="space-y-2">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Orientacao das fontes
        </p>
        <div className="flex h-4 overflow-hidden rounded-full">
          {supportPct > 0 && (
            <div
              className="bg-green-500 transition-all"
              style={{ width: `${supportPct}%` }}
            />
          )}
          {contradictPct > 0 && (
            <div
              className="bg-red-500 transition-all"
              style={{ width: `${contradictPct}%` }}
            />
          )}
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-green-600 dark:text-green-400">
            {supportCount} suportam ({supportPct}%)
          </span>
          <span className="text-red-600 dark:text-red-400">
            {contradictCount} contradizem ({contradictPct}%)
          </span>
        </div>
      </div>

      {/* Diversity metrics */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-gray-100 p-3 text-center dark:border-gray-800">
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {sourceTypes.size}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Tipos de fonte
          </div>
        </div>
        <div className="rounded-lg border border-gray-100 p-3 text-center dark:border-gray-800">
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {domainCount}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Dominios
          </div>
        </div>
        <div className="rounded-lg border border-gray-100 p-3 text-center dark:border-gray-800">
          <div className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {reliableCount}/{sources.length}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Alta fiabilidade
          </div>
        </div>
      </div>

      {/* Source type breakdown */}
      <div className="space-y-1">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Por tipo de fonte
        </p>
        {Array.from(sourceTypes).map((type) => {
          const typeCount = sources.filter(
            (s) => s.source.source_type === type,
          ).length;
          const pct = Math.round((typeCount / sources.length) * 100);
          return (
            <div key={type} className="flex items-center gap-2">
              <span className="w-24 text-xs text-gray-600 dark:text-gray-400">
                {type}
              </span>
              <div className="flex-1">
                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
                  <div
                    className="h-2 rounded-full bg-blue-500"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </div>
              <span className="w-8 text-right text-xs tabular-nums text-gray-400">
                {typeCount}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
