'use client';

import { useState, FormEvent, useRef } from 'react';
import { useRouter } from 'next/navigation';
import ProtectedRoute from '@/components/ProtectedRoute';
import Navbar from '@/components/Navbar';
import { createIncident } from '@/lib/api';

const STEPS = ['Describe', 'Locate', 'Evidence', 'Review'];

const SEVERITY_OPTIONS = [
  { value: '', label: 'Unsure (let AI decide)' },
  { value: 'P1', label: 'P1 — Critical outage' },
  { value: 'P2', label: 'P2 — Major degradation' },
  { value: 'P3', label: 'P3 — Partial impact' },
  { value: 'P4', label: 'P4 — Minor issue' },
  { value: 'P5', label: 'P5 — Cosmetic' },
];

export default function NewIncidentPage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState(0);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [service, setService] = useState('');
  const [reporterSeverity, setReporterSeverity] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function canAdvance(): boolean {
    switch (step) {
      case 0: return title.length >= 5 && description.length >= 10;
      case 1: return true;
      case 2: return true;
      case 3: return true;
      default: return false;
    }
  }

  function handleNext() {
    if (canAdvance()) {
      setStep(step + 1);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      const arr = Array.from(e.target.files);
      // Block SVG
      const filtered = arr.filter(f => !f.name.endsWith('.svg'));
      if (filtered.length !== arr.length) {
        setError('SVG files are not allowed (XSS risk)');
      } else {
        setError('');
      }
      // Size caps
      const oversized = filtered.filter(f => f.size > 5 * 1024 * 1024);
      if (oversized.length > 0) {
        setError(`Files too large (max 5MB each): ${oversized.map(f => f.name).join(', ')}`);
        return;
      }
      setFiles(filtered);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);
      formData.append('service', service || 'unknown');
      if (reporterSeverity) {
        formData.append('reporter_severity', reporterSeverity);
      }
      files.forEach((f) => {
        formData.append('evidence', f);
      });

      const incident = await createIncident(formData);
      router.push(`/incidents/${incident.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit incident');
    } finally {
      setLoading(false);
    }
  }

  function StepIndicator() {
    return (
      <div className="flex items-center gap-2 mb-8">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${
              i <= step ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-500'
            }`}>
              {i + 1}
            </div>
            <span className={`text-sm ${i <= step ? 'text-white' : 'text-gray-600'}`}>{label}</span>
            {i < STEPS.length - 1 && <div className="w-8 h-px bg-gray-700" />}
          </div>
        ))}
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-950 text-white">
        <Navbar />
        <main className="mx-auto max-w-2xl px-4 py-8">
          <StepIndicator />

          <form onSubmit={handleSubmit}>
            {error && (
              <div className="mb-6 rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-400">
                {error}
              </div>
            )}

            {/* Step 0: Describe */}
            {step === 0 && (
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2.5 text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    placeholder="Brief summary (5+ characters)"
                    required
                    minLength={5}
                    maxLength={200}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Description</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={6}
                    className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2.5 text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    placeholder="What is happening? Include error messages, stack traces, or any relevant details. (10+ characters)"
                    required
                    minLength={10}
                    maxLength={5000}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Initial Severity Estimate</label>
                  <select
                    value={reporterSeverity}
                    onChange={(e) => setReporterSeverity(e.target.value)}
                    className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2.5 text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  >
                    {SEVERITY_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}

            {/* Step 1: Locate */}
            {step === 1 && (
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Affected Service / Area</label>
                  <input
                    type="text"
                    value={service}
                    onChange={(e) => setService(e.target.value)}
                    className="w-full rounded-lg border border-gray-700 bg-gray-900 px-4 py-2.5 text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    placeholder="e.g., checkout, payments, database, auth"
                    maxLength={100}
                  />
                </div>
                <div className="rounded-lg bg-gray-900 border border-gray-800 px-4 py-3">
                  <p className="text-sm text-gray-400">
                    Leave blank or enter &quot;unknown&quot; if you&apos;re not sure which service is affected.
                    The AI agent will attempt to identify the relevant module automatically.
                  </p>
                </div>
              </div>
            )}

            {/* Step 2: Evidence */}
            {step === 2 && (
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Attach Evidence (optional)</label>
                  <div
                    onClick={() => fileRef.current?.click()}
                    className="mt-1 flex justify-center rounded-lg border-2 border-dashed border-gray-700 px-6 py-10 hover:border-gray-500 cursor-pointer transition-colors"
                  >
                    <div className="text-center">
                      <p className="text-sm text-gray-400">
                        Click to upload screenshots, log files, or error dumps
                      </p>
                      <p className="mt-1 text-xs text-gray-600">
                        PNG, JPG, GIF, WebP, MP4, WebM, .log, .txt, .json (max 5MB each)
                      </p>
                    </div>
                  </div>
                  <input
                    ref={fileRef}
                    type="file"
                    multiple
                    onChange={handleFileChange}
                    className="hidden"
                    accept=".png,.jpg,.jpeg,.gif,.webp,.mp4,.webm,.log,.txt,.json"
                  />
                </div>
                {files.length > 0 && (
                  <div className="space-y-2">
                    {files.map((f, i) => (
                      <div key={i} className="flex items-center justify-between rounded-lg bg-gray-900 border border-gray-800 px-4 py-2">
                        <span className="text-sm text-gray-300 truncate">{f.name}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-xs text-gray-500">{(f.size / 1024).toFixed(1)}KB</span>
                          <button
                            type="button"
                            onClick={() => setFiles(files.filter((_, j) => j !== i))}
                            className="text-red-400 hover:text-red-300 text-sm"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Step 3: Review */}
            {step === 3 && (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-300">Review your incident report</h3>
                <div className="rounded-lg bg-gray-900 border border-gray-800 divide-y divide-gray-800">
                  <div className="px-4 py-3">
                    <p className="text-xs text-gray-500 mb-1">Title</p>
                    <p className="text-sm text-white">{title}</p>
                  </div>
                  <div className="px-4 py-3">
                    <p className="text-xs text-gray-500 mb-1">Description</p>
                    <p className="text-sm text-gray-300 whitespace-pre-wrap">{description}</p>
                  </div>
                  <div className="px-4 py-3 flex justify-between">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Service</p>
                      <p className="text-sm text-white">{service || 'unknown'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Severity</p>
                      <p className="text-sm text-white">{reporterSeverity || 'AI will decide'}</p>
                    </div>
                  </div>
                  <div className="px-4 py-3">
                    <p className="text-xs text-gray-500 mb-1">Evidence</p>
                    <p className="text-sm text-white">
                      {files.length > 0 ? files.map(f => f.name).join(', ') : 'None'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="mt-8 flex justify-between">
              {step > 0 ? (
                <button
                  type="button"
                  onClick={() => setStep(step - 1)}
                  className="rounded-lg border border-gray-700 px-5 py-2.5 text-sm font-semibold text-gray-300 hover:bg-gray-800 transition-colors"
                >
                  Back
                </button>
              ) : (
                <div />
              )}

              {step < STEPS.length - 1 ? (
                <button
                  type="button"
                  onClick={handleNext}
                  disabled={!canAdvance()}
                  className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-lg bg-green-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Submitting...' : 'Submit Incident'}
                </button>
              )}
            </div>
          </form>
        </main>
      </div>
    </ProtectedRoute>
  );
}
