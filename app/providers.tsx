"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

/** Provides TanStack Query state for backend calls made by client components. */
export function Providers({ children }: { children: React.ReactNode }): JSX.Element {
  const [client] = useState(() => new QueryClient());
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
