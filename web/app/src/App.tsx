import { Header } from "./components/Header";
import { ExperimentScreen } from "./features/experiment/ExperimentScreen";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-slate-50">
      <Header />
      <ExperimentScreen />
    </div>
  );
}
