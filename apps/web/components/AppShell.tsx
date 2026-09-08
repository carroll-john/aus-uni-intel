import Link from "next/link";
import { BarChart3, Building2, GitCompare, ListOrdered, Sparkles, TableProperties } from "lucide-react";

const nav = [
  { href: "/", label: "Sector overview", icon: BarChart3 },
  { href: "/providers", label: "Providers", icon: Building2 },
  { href: "/rankings", label: "Rankings", icon: ListOrdered },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/data-picture", label: "Data Picture Studio", icon: Sparkles },
  { href: "/sources", label: "Sources", icon: TableProperties }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen text-ink">
      <aside className="fixed inset-y-0 left-0 hidden w-72 bg-navy px-5 py-6 text-white lg:block">
        <div className="mb-8 flex items-center gap-3">
          <img alt="Keypath Education" className="h-auto w-36 brightness-0 invert" src="/keypath/keypath-logo.svg" />
          <div>
            <div className="mt-2 text-xs font-semibold uppercase tracking-[0.16em] text-gold">University intelligence</div>
          </div>
        </div>
        <nav className="space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                className="flex items-center gap-3 rounded-md px-3 py-2 text-sm font-semibold text-white/80 hover:bg-white/10 hover:text-gold"
                href={item.href}
                key={item.href}
              >
                <Icon size={17} />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-6 left-5 right-5 border-t border-white/15 pt-5 text-xs leading-5 text-white/70">
          Source-backed public data for Australian higher education benchmarks.
        </div>
      </aside>
      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-line bg-white/95 px-4 py-3 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="kp-eyebrow">Australian university intelligence</div>
              <div className="mt-1 text-sm font-semibold text-ink">Finance, student, research, and QILT public data</div>
            </div>
            <div className="rounded-full border border-gold bg-gold px-4 py-2 text-xs font-bold uppercase tracking-[0.14em] text-navy">
              Source-backed
            </div>
          </div>
          <nav className="mt-3 flex gap-2 overflow-x-auto pb-1 lg:hidden">
            {nav.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  className="flex shrink-0 items-center gap-2 rounded-full border border-line bg-white px-3 py-2 text-xs font-semibold text-ink"
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
        <main className="px-4 py-7 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
