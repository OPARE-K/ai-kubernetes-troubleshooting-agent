"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { insforge } from "@/lib/insforge";

interface AuthUser {
  id: string;
  email: string;
  profile?: { name?: string };
}

export type AuthActionResult =
  | { kind: "success"; message?: string }
  | { kind: "verify_email" }
  | { kind: "error"; message: string };

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<AuthActionResult>;
  signUp: (email: string, password: string, name: string) => Promise<AuthActionResult>;
  verifyEmail: (email: string, otp: string) => Promise<AuthActionResult>;
  resendVerificationEmail: (email: string) => Promise<AuthActionResult>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function mapProfile(
  profile: { name?: string } | null | undefined
): { name?: string } | undefined {
  if (!profile) return undefined;
  return { name: profile.name };
}

function isVerificationRequired(error: {
  message?: string;
  error?: string;
}): boolean {
  const message = (error.message ?? "").toLowerCase();
  const code = (error.error ?? "").toLowerCase();
  return (
    message.includes("verification") ||
    message.includes("verify") ||
    message.includes("not verified") ||
    code.includes("verify") ||
    code.includes("email_not_verified")
  );
}

function formatOtpError(error: { message?: string; error?: string }): string {
  const message = (error.message ?? "").toLowerCase();
  const code = (error.error ?? "").toLowerCase();

  if (message.includes("expired") || code.includes("expired")) {
    return "That code has expired. Request a new one and try again.";
  }
  if (message.includes("invalid") || code.includes("invalid")) {
    return "Invalid verification code. Check the email and try again.";
  }
  if (message.includes("missing") || code.includes("missing")) {
    return "Enter the 6-digit verification code from your email.";
  }

  return error.message ?? "Verification failed. Please try again.";
}

function setUserFromResponse(
  setUser: (user: AuthUser | null) => void,
  user: { id: string; email: string; profile?: { name?: string } | null }
) {
  setUser({
    id: user.id,
    email: user.email,
    profile: mapProfile(user.profile),
  });
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadUser = useCallback(async () => {
    const { data, error } = await insforge.auth.getCurrentUser();
    if (error || !data.user) {
      setUser(null);
      return;
    }
    setUserFromResponse(setUser, data.user);
  }, []);

  useEffect(() => {
    loadUser().finally(() => setIsLoading(false));
  }, [loadUser]);

  const signIn = useCallback(async (email: string, password: string) => {
    const { data, error } = await insforge.auth.signInWithPassword({
      email,
      password,
    });
    if (error) {
      if (isVerificationRequired(error)) {
        return { kind: "verify_email" as const };
      }
      return { kind: "error" as const, message: error.message ?? "Sign in failed" };
    }
    if (data?.user) {
      setUserFromResponse(setUser, data.user);
    }
    return { kind: "success" as const };
  }, []);

  const signUp = useCallback(async (email: string, password: string, name: string) => {
    const { data, error } = await insforge.auth.signUp({
      email,
      password,
      name,
    });
    if (error) {
      return { kind: "error" as const, message: error.message ?? "Sign up failed" };
    }
    if (data?.requireEmailVerification) {
      return { kind: "verify_email" as const };
    }
    if (data?.user && data.accessToken) {
      setUserFromResponse(setUser, data.user);
    }
    return { kind: "success" as const };
  }, []);

  const verifyEmail = useCallback(async (email: string, otp: string) => {
    const trimmedOtp = otp.trim();
    if (!trimmedOtp) {
      return {
        kind: "error" as const,
        message: "Enter the 6-digit verification code from your email.",
      };
    }

    const { data, error } = await insforge.auth.verifyEmail({
      email,
      otp: trimmedOtp,
    });
    if (error) {
      return { kind: "error" as const, message: formatOtpError(error) };
    }
    if (data?.user) {
      setUserFromResponse(setUser, data.user);
    }
    return { kind: "success" as const };
  }, []);

  const resendVerificationEmail = useCallback(async (email: string) => {
    const { data, error } = await insforge.auth.resendVerificationEmail({ email });
    if (error) {
      return {
        kind: "error" as const,
        message: error.message ?? "Could not resend verification email",
      };
    }
    return {
      kind: "success" as const,
      message: data?.message ?? "Verification code sent. Check your email.",
    };
  }, []);

  const signOut = useCallback(async () => {
    await insforge.auth.signOut();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isLoading,
      signIn,
      signUp,
      verifyEmail,
      resendVerificationEmail,
      signOut,
    }),
    [user, isLoading, signIn, signUp, verifyEmail, resendVerificationEmail, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
