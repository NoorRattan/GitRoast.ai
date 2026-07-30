"use client";

import { Component, type ReactNode } from "react";

type SceneErrorBoundaryProps = {
  children: ReactNode;
  fallback: ReactNode;
  onError?: () => void;
};

type SceneErrorBoundaryState = {
  hasError: boolean;
};

export class SceneErrorBoundary extends Component<SceneErrorBoundaryProps, SceneErrorBoundaryState> {
  state: SceneErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): SceneErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(): void {
    this.props.onError?.();
  }

  render(): ReactNode {
    return this.state.hasError ? this.props.fallback : this.props.children;
  }
}
