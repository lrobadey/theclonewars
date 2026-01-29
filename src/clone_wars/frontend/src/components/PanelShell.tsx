import type { ReactNode } from "react";

export default function PanelShell({
  title,
  tone,
  children
}: {
  title: string;
  tone?: string;
  children: ReactNode;
}) {
  const toneKey = tone?.replace("tone-", "");
  const panelTone = toneKey ? `panel-tone-${toneKey}` : "";

  return (
    <div className={`panel panel-live p-5 space-y-4 ${panelTone}`.trim()}>
      <div className="flex items-center justify-between">
        <h2 className={`text-lg ${tone ?? ""}`}>{title}</h2>
      </div>
      {children}
    </div>
  );
}
