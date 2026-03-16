import {
  Landmark,
  TrendingUp,
  Cpu,
  Heart,
  FlaskConical,
  Users,
  Palette,
  Trophy,
  Globe,
  Tag,
  type LucideIcon,
} from "lucide-react";
import { getAreaColor } from "@/lib/utils/certainty-color";
import { humanizeTag } from "@/lib/utils/humanize-tag";

const areaIcons: Record<string, LucideIcon> = {
  politica: Landmark,
  economia: TrendingUp,
  tecnologia: Cpu,
  saude: Heart,
  ciencia: FlaskConical,
  sociedade: Users,
  cultura: Palette,
  desporto: Trophy,
  mundo: Globe,
};

function normalizeArea(area: string): string {
  return area
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

interface AreaChipProps {
  area: string;
  size?: "sm" | "md";
}

export function AreaChip({ area, size = "sm" }: AreaChipProps) {
  const normalized = normalizeArea(area);
  const Icon = areaIcons[normalized] || Tag;
  const color = getAreaColor(area);

  const sizeClasses =
    size === "sm"
      ? "px-2 py-0.5 text-xs gap-1"
      : "px-3 py-1 text-sm gap-1.5";

  const iconSize = size === "sm" ? 12 : 14;

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${sizeClasses}`}
      style={{
        color,
        backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`,
        border: `1px solid color-mix(in srgb, ${color} 25%, transparent)`,
      }}
    >
      <Icon size={iconSize} />
      {humanizeTag(area)}
    </span>
  );
}
