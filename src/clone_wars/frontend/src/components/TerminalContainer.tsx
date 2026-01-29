import type { ReactNode } from "react";

export default function TerminalContainer({ children }: { children: ReactNode }) {
  return <div className="crt-shell">{children}</div>;
}
