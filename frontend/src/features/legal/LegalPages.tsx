import type { ReactNode } from "react";

import { useTranslation } from "../../shared/i18n";

function LegalLayout({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  const { t } = useTranslation();

  return (
    <article className="mx-auto max-w-3xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
      <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">{t("legal.eyebrow")}</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{title}</h1>
      <div className="mt-8 space-y-7 text-slate-700">{children}</div>
    </article>
  );
}

export function PrivacyPage() {
  const { t } = useTranslation();

  return (
    <LegalLayout title={t("privacy.title")}>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("privacy.collectHeading")}</h2>
        <p className="mt-2 leading-7">{t("privacy.collectBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("privacy.loansHeading")}</h2>
        <p className="mt-2 leading-7">{t("privacy.loansBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("privacy.filesHeading")}</h2>
        <p className="mt-2 leading-7">{t("privacy.filesBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("privacy.assistantHeading")}</h2>
        <p className="mt-2 leading-7">{t("privacy.assistantBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("privacy.securityHeading")}</h2>
        <p className="mt-2 leading-7">{t("privacy.securityBody")}</p>
      </section>
    </LegalLayout>
  );
}

export function TermsPage() {
  const { t } = useTranslation();

  return (
    <LegalLayout title={t("terms.title")}>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("terms.scopeHeading")}</h2>
        <p className="mt-2 leading-7">{t("terms.scopeBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("terms.accountHeading")}</h2>
        <p className="mt-2 leading-7">{t("terms.accountBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("terms.useHeading")}</h2>
        <p className="mt-2 leading-7">{t("terms.useBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("terms.aiHeading")}</h2>
        <p className="mt-2 leading-7">{t("terms.aiBody")}</p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">{t("terms.availabilityHeading")}</h2>
        <p className="mt-2 leading-7">{t("terms.availabilityBody")}</p>
      </section>
    </LegalLayout>
  );
}
