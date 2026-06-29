import { safeHttpUrl } from "@/lib/safe-url";

type SafeExternalLinkProps = {
  href: string | null | undefined;
  className?: string;
  children: React.ReactNode;
};

export function SafeExternalLink({ href, className, children }: SafeExternalLinkProps) {
  const safeHref = safeHttpUrl(href);
  if (!safeHref) return null;

  return (
    <a className={className} href={safeHref} rel="noopener noreferrer" target="_blank">
      {children}
    </a>
  );
}
