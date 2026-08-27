import type { ReactNode } from "react";

function LegalLayout({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <article className="mx-auto max-w-3xl rounded-3xl border border-slate-200 bg-white p-8 shadow-sm sm:p-10">
      <p className="text-sm font-medium uppercase tracking-[0.18em] text-sky-700">{eyebrow}</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">{title}</h1>
      <div className="mt-8 space-y-7 text-slate-700">{children}</div>
    </article>
  );
}

export function PrivacyPage() {
  return (
    <LegalLayout eyebrow="LibraryOS policies" title="Privacy Policy">
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Information we collect</h2>
        <p className="mt-2 leading-7">
          Account and profile data, including the email, display name, and biography you provide, are stored so LibraryOS can authenticate your account and show the public fields you choose to share. Email and authentication data remain private to the account owner and authorized administrators.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Borrowing history</h2>
        <p className="mt-2 leading-7">
          Loan records are used to show your active and previous borrowing activity, protect inventory, and calculate due dates. They are not displayed on public profiles.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Files and images</h2>
        <p className="mt-2 leading-7">
          Uploaded assets used for library work are stored in the application&#39;s private file volume and are served only through authorized application routes.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Assistant prompts</h2>
        <p className="mt-2 leading-7">
          Prompts sent to the LibraryOS assistant are processed to generate a response. Gemini, Google&#39;s third-party AI service, may process those prompts under its applicable service terms. Do not include passwords, payment details, or other sensitive information in an AI prompt.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Security and choices</h2>
        <p className="mt-2 leading-7">
          Sessions use secure, HttpOnly cookies. You can update your details through the application and ask the project operator about data removal. This policy describes the educational demo&#39;s current behavior and may be updated as the project evolves.
        </p>
      </section>
    </LegalLayout>
  );
}

export function TermsPage() {
  return (
    <LegalLayout eyebrow="LibraryOS policies" title="Terms of Service">
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Scope of this service</h2>
        <p className="mt-2 leading-7">
          LibraryOS is an educational library-management demonstration. It is not a replacement for a production circulation, identity, or records-management system.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Account responsibility</h2>
        <p className="mt-2 leading-7">
          Keep your sign-in details private, provide truthful profile information, and review activity performed through your account. Tell the project operator if you believe an account has been used without permission.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Acceptable use</h2>
        <p className="mt-2 leading-7">
          Use the service respectfully and lawfully. Do not probe, overload, bypass access controls, upload harmful content, or use another person&#39;s private account data.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">AI response limitations</h2>
        <p className="mt-2 leading-7">
          AI responses are informational and may be incomplete or wrong. Verify catalog, loan, and other important facts in the application before relying on them.
        </p>
      </section>
      <section>
        <h2 className="text-lg font-semibold text-slate-950">Service availability</h2>
        <p className="mt-2 leading-7">
          The demo is provided as available, without a promise of uninterrupted access, data retention, or a particular response time. Features may change while the project is developed and evaluated.
        </p>
      </section>
    </LegalLayout>
  );
}
