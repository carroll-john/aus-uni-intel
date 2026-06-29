import Link from "next/link";
import { BarChart3, Building2, GitCompare, ListOrdered, ShieldCheck, TableProperties } from "lucide-react";

const nav = [
  { href: "/", label: "Sector overview", icon: BarChart3 },
  { href: "/providers", label: "Providers", icon: Building2 },
  { href: "/rankings", label: "Rankings", icon: ListOrdered },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/sources", label: "Sources", icon: TableProperties }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f7f9fb] text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-line bg-white px-4 py-5 lg:block">
        <div className="mb-8 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-teal text-white">
            <ShieldCheck size={19} />
          </div>
          <div>
            <div className="text-sm font-semibold">Uni Intel</div>
            <div className="text-xs text-muted">Source-backed public data</div>
          </div>
        </div>
        <nav className="space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-ink hover:bg-slate-100"
                href={item.href}
                key={item.href}
              >
                <Icon size={17} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-line bg-white/95 px-4 py-3 backdrop-blur lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold">Australian university intelligence</div>
              <div className="text-xs text-muted">Finance 2024, student data, HERDC, QILT SES</div>
            </div>
            <div className="rounded-md border border-line px-3 py-1.5 text-xs font-medium text-teal">
              Source-backed
            </div>
          </div>
          <nav className="mt-3 flex gap-2 overflow-x-auto pb-1 lg:hidden">
            {nav.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  className="flex shrink-0 items-center gap-2 rounded-md border border-line px-3 py-2 text-xs font-medium"
                  href={item.href}
                  key={item.href}
                >
                  <Icon size={14} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
