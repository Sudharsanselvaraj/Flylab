import { Header } from "./components/Header";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { ExperimentScreen } from "./features/experiment/ExperimentScreen";

export default function App() {
  return (
    <ErrorBoundary
      fallback={(issue: string) => (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
          <div className="max-w-md w-full rounded-xl bg-white border border-red-200 p-6 text-center">
            <h2 className="text-lg font-semibold text-slate-800">The app hit an error</h2>
            <p className="mt-2 text-sm text-slate-500">{issue}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 rounded-lg bg-slate-900 text-white text-sm px-4 py-2 hover:bg-slate-700"
            >
              Reload
            </button>
          </div>
        </div>
      )}
    >
      <div className="min-h-screen flex flex-col bg-slate-50">
        <Header />
        <ExperimentScreen />
      </div>
    </ErrorBoundary>
  );
}
