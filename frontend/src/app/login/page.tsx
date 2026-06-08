"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { useAuth } from "@/contexts/AuthContext";

type AuthMode = "signin" | "signup" | "verify";

export default function LoginPage() {
  const router = useRouter();
  const { signIn, signUp, verifyEmail, resendVerificationEmail } = useAuth();
  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResending, setIsResending] = useState(false);

  const goToVerify = (message: string) => {
    setError(null);
    setInfo(message);
    setOtp("");
    setMode("verify");
  };

  const handleAuthSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setIsSubmitting(true);

    const result =
      mode === "signin"
        ? await signIn(email, password)
        : await signUp(email, password, name);

    setIsSubmitting(false);

    if (result.kind === "verify_email") {
      goToVerify(
        mode === "signup"
          ? "We sent a 6-digit verification code to your email. Enter it below to continue."
          : "Email verification is required. Enter the 6-digit code we sent to your email."
      );
      return;
    }

    if (result.kind === "error") {
      setError(result.message);
      return;
    }

    router.replace("/dashboard");
  };

  const handleVerifySubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setInfo(null);
    setIsSubmitting(true);

    const result = await verifyEmail(email, otp);

    setIsSubmitting(false);

    if (result.kind === "error") {
      setError(result.message);
      return;
    }

    router.replace("/dashboard");
  };

  const handleResend = async () => {
    if (!email.trim()) {
      setError("Enter your email address to resend the verification code.");
      return;
    }

    setError(null);
    setInfo(null);
    setIsResending(true);

    const result = await resendVerificationEmail(email);

    setIsResending(false);

    if (result.kind === "error") {
      setError(result.message);
      return;
    }

    if (result.kind === "success") {
      setInfo(result.message ?? "Verification code sent. Check your email.");
    }
  };

  const subtitle =
    mode === "verify"
      ? "Enter the verification code sent to your email"
      : mode === "signin"
        ? "Sign in to investigate your cluster"
        : "Create an account";

  const modeLabel =
    mode === "verify" ? "Verify Email" : mode === "signin" ? "Sign In" : "Sign Up";

  return (
    <main className="app-background flex min-h-screen items-center justify-center px-6 py-12 text-white">
      <div className="w-full max-w-md animate-fade-in">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500/20 to-blue-600/20 ring-1 ring-sky-500/30">
            <svg
              className="h-7 w-7 text-sky-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
              aria-hidden
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 7.5V18a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18V7.5m18 0A2.25 2.25 0 0018.75 5.25H5.25A2.25 2.25 0 003 7.5m18 0H3"
              />
            </svg>
          </div>
          <h1 className="bg-gradient-to-r from-white to-slate-300 bg-clip-text text-2xl font-bold tracking-tight text-transparent">
            AI Kubernetes Agent
          </h1>
          <p className="mt-2 text-sm text-slate-400">{subtitle}</p>
        </div>

        <div className="glass-card-accent p-8">
          <div className="mb-6 flex rounded-xl bg-slate-950/50 p-1 ring-1 ring-white/5">
            {(["signin", "signup"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => {
                  if (mode !== "verify") {
                    setMode(tab);
                    setError(null);
                    setInfo(null);
                  }
                }}
                disabled={mode === "verify"}
                className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
                  mode === tab
                    ? "bg-sky-600/80 text-white shadow-sm"
                    : mode === "verify"
                      ? "cursor-not-allowed text-slate-600"
                      : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab === "signin" ? "Sign In" : "Sign Up"}
              </button>
            ))}
          </div>

          <p className="mb-5 text-center text-xs font-medium uppercase tracking-wider text-slate-500">
            {modeLabel}
          </p>

          {mode === "verify" ? (
            <form onSubmit={handleVerifySubmit} className="space-y-4">
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                required
              />
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                placeholder="6-digit verification code"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                className="input-field text-center text-lg tracking-[0.4em]"
                required
                minLength={6}
                maxLength={6}
                pattern="\d{6}"
              />
              {error ? <div className="alert-error">{error}</div> : null}
              {info ? <div className="alert-success">{info}</div> : null}
              <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
                {isSubmitting ? "Verifying..." : "Verify email"}
              </button>
              <button
                type="button"
                onClick={handleResend}
                disabled={isResending || isSubmitting}
                className="btn-secondary w-full"
              >
                {isResending ? "Sending..." : "Resend code"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode("signin");
                  setError(null);
                  setInfo(null);
                  setOtp("");
                }}
                className="btn-ghost w-full py-2"
              >
                Back to sign in
              </button>
            </form>
          ) : (
            <>
              <form onSubmit={handleAuthSubmit} className="space-y-4">
                {mode === "signup" ? (
                  <input
                    type="text"
                    placeholder="Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input-field"
                    required
                  />
                ) : null}
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field"
                  required
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field"
                  required
                  minLength={6}
                />
                {error ? <div className="alert-error">{error}</div> : null}
                {info ? <div className="alert-success">{info}</div> : null}
                <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
                  {isSubmitting
                    ? "Please wait..."
                    : mode === "signin"
                      ? "Sign in"
                      : "Sign up"}
                </button>
              </form>

              <button
                type="button"
                onClick={() => {
                  setMode(mode === "signin" ? "signup" : "signin");
                  setError(null);
                  setInfo(null);
                }}
                className="btn-ghost mt-5 w-full py-2"
              >
                {mode === "signin"
                  ? "Need an account? Sign up"
                  : "Already have an account? Sign in"}
              </button>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
