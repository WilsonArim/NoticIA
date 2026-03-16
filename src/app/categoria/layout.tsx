import { PipelineTicker } from "@/components/ui/PipelineTicker";
import { Hero3D } from "@/components/3d/Hero3D";

export default function CategoriaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <PipelineTicker />
      <Hero3D />
      {children}
    </>
  );
}
