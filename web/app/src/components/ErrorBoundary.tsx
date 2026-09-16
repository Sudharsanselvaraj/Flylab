import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: (issue: string) => ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error) {
    console.error("[ErrorBoundary]", error);
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback) return this.props.fallback(this.state.error.message);
      return (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
          <p className="font-medium">View failed to render</p>
          <p className="mt-1 text-xs text-amber-700">{this.state.error.message}</p>
        </div>
      );
    }
    return this.props.children;
  }
}