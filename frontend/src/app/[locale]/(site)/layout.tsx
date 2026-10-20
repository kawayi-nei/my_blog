import SiteFooter from '@/components/site-footer';
import SiteHeader from '@/components/site-header';
import {getSiteConfig} from '@/lib/api';

export default async function SiteLayout({
  children
}: {
  children: React.ReactNode;
}) {
  let adminEnabled = false;
  try {
    adminEnabled = (await getSiteConfig()).admin_enabled;
  } catch {
    adminEnabled = false;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader adminEnabled={adminEnabled} />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  );
}
