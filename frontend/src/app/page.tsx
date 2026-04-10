import Link from 'next/link';
import Navbar from '@/components/Navbar';

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Navbar />
      <main className="flex flex-col items-center justify-center" style={{ minHeight: 'calc(100vh - 3.5rem)' }}>
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
    </div>
  );
}
