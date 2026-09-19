import { PhysicalCodingLab } from "./features/coding/PhysicalCodingLab";
import { ErrorBoundary } from "./components/ErrorBoundary";

export default function App() {
  return <ErrorBoundary><PhysicalCodingLab /></ErrorBoundary>;
}
