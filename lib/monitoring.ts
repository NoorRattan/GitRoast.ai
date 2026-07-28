let sentryInitialized = false;

export async function captureFrontendError(error: Error): Promise<void> {
  const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;
  if (dsn) {
    const Sentry = await import("@sentry/browser");
    if (!sentryInitialized) {
      Sentry.init({
        dsn,
        sendDefaultPii: false,
        tracesSampleRate: 0
      });
      sentryInitialized = true;
    }
    Sentry.captureException(error);
  }

  // Keep failures visible when centralized monitoring is not configured.
  // eslint-disable-next-line no-console
  console.error("GitRoast frontend error", error);
}
