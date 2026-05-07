"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import GoogleButton from "@/components/auth/GoogleButton";
import { ApiError, authApi } from "@/lib/api";

const oauthErrorMessages: Record<string, string> = {
  oauth_denied: "Google 로그인이 취소되었습니다.",
  oauth_invalid: "잘못된 OAuth 응답입니다.",
  oauth_state_mismatch: "보안 검증에 실패했습니다. 다시 시도해주세요.",
  oauth_failed: "Google 로그인에 실패했습니다.",
};

export default function LoginPage() {
  return (
    <Card className="p-8">
      <h1 className="text-2xl font-light tracking-tight mb-1">로그인</h1>
      <p className="text-sm text-white/50 mb-8">chord_ai 계정으로 계속하기</p>

      <Suspense fallback={null}>
        <OAuthError />
      </Suspense>

      <LoginForm />

      <Divider />

      <GoogleButton label="Google로 계속하기" />

      <p className="mt-8 text-center text-xs text-white/50">
        계정이 없으신가요?{" "}
        <Link href="/signup" className="text-white hover:underline">
          회원가입
        </Link>
      </p>
    </Card>
  );
}

function OAuthError() {
  const params = useSearchParams();
  const oauthError = params.get("error");
  if (!oauthError || !oauthErrorMessages[oauthError]) return null;
  return (
    <div className="mb-4 px-4 py-3 rounded-2xl bg-red-500/10 border border-red-500/20 text-xs text-red-300">
      {oauthErrorMessages[oauthError]}
    </div>
  );
}

function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await authApi.login(email, password);
      router.push("/");
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("로그인 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <Input
        name="email"
        type="email"
        label="이메일"
        autoComplete="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <Input
        name="password"
        type="password"
        label="비밀번호"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        error={error ?? undefined}
      />
      <Button type="submit" loading={submitting} className="mt-2">
        로그인
      </Button>
    </form>
  );
}

function Divider() {
  return (
    <div className="my-6 flex items-center gap-3">
      <span className="flex-1 h-px bg-white/8" />
      <span className="text-xs text-white/40">또는</span>
      <span className="flex-1 h-px bg-white/8" />
    </div>
  );
}
