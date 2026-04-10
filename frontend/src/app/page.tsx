import Link from 'next/link';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-950 text-white">
      <h1 className="text-6xl font-bold tracking-tight">Cerno</h1>
      <p className="mt-4 text-xl text-gray-400">
        SRE Incident Intake &amp; Triage Agent
      </p>
      <div className="mt-10 flex gap-4">
        <Link
          href="/incidents/new"
          className="rounded-lg bg-indigo-600 px-6 py-3 font-semibold hover:bg-indigo-500 transition-colors"
        >
          Report Incident
        </Link>
        <Link
          href="/dashboard"
          className="rounded-lg border border-gray-700 px-6 py-3 font-semibold hover:bg-gray-800 transition-colors"
        >
          Dashboard
        </Link>
      </div>
    </main>
  );
}
