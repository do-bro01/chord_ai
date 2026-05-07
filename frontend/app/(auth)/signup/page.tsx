"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { Check } from "lucide-react";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import GoogleButton from "@/components/auth/GoogleButton";
import { ApiError, authApi } from "@/lib/api";

type Step = 1 | 2 | 3 | 4;

export default function SignupPage() {
  const [step, setStep] = useState<Step>(1);
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");

  return (
    <Card className="p-8">
      <h1 className="text-2xl font-light tracking-tight mb-1">회원가입</h1>
      <p className="text-sm text-white/50 mb-6">
        {step === 1 && "이메일로 인증코드를 받아주세요"}
        {step === 2 && `${email} 로 보낸 인증코드를 입력하세요`}
        {step === 3 && "사용할 비밀번호를 설정해주세요"}
        {step === 4 && "환영합니다"}
      </p>

      <StepIndicator step={step} />

      <div className="mt-8">
        {step === 1 && (
          <EmailStep
            email={email}
            setEmail={setEmail}
            onNext={() => setStep(2)}
          />
        )}
        {step === 2 && (
          <CodeStep
            email={email}
            code={code}
            setCode={setCode}
            onBack={() => setStep(1)}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <PasswordStep
            email={email}
            code={code}
            onBack={() => setStep(2)}
            onComplete={() => setStep(4)}
          />
        )}
        {step === 4 && <DoneStep />}
      </div>

      {step === 1 ? (
        <>
          <Divider />
          <GoogleButton label="Google로 가입" />
          <p className="mt-8 text-center text-xs text-white/50">
            이미 계정이 있으신가요?{" "}
            <Link href="/login" className="text-white hover:underline">
              로그인
            </Link>
          </p>
        </>
      ) : null}
    </Card>
  );
}

function StepIndicator({ step }: { step: Step }) {
  return (
    <div className="flex items-center justify-center gap-2">
      {[1, 2, 3, 4].map((n) => (
        <span
          key={n}
          className={`h-1.5 rounded-full transition-all ${
            n === step ? "w-6 bg-white" : "w-1.5 bg-white/25"
          }`}
        />
      ))}
    </div>
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

// ---------- Step 1: 이메일 ----------

function EmailStep({
  email,
  setEmail,
  onNext,
}: {
  email: string;
  setEmail: (v: string) => void;
  onNext: () => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await authApi.requestSignupCode(email);
      onNext();
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("인증코드 발송 중 오류가 발생했습니다.");
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
        error={error ?? undefined}
      />
      <Button type="submit" loading={submitting}>
        인증코드 받기
      </Button>
    </form>
  );
}

// ---------- Step 2: 인증코드 ----------

const COOLDOWN = 60;

function CodeStep({
  email,
  code,
  setCode,
  onBack,
  onNext,
}: {
  email: string;
  code: string;
  setCode: (v: string) => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const initialDigits = (() => {
    const d = Array(6).fill("");
    for (let i = 0; i < Math.min(code.length, 6); i++) d[i] = code[i];
    return d;
  })();
  const [digits, setDigits] = useState<string[]>(initialDigits);
  const [error, setError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(COOLDOWN);
  const inputs = useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const setDigit = (i: number, v: string) => {
    const digit = v.replace(/\D/g, "").slice(-1);
    const next = [...digits];
    next[i] = digit;
    setDigits(next);
    if (digit && i < 5) inputs.current[i + 1]?.focus();
  };

  const onKeyDown = (i: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[i] && i > 0) {
      inputs.current[i - 1]?.focus();
    }
  };

  const onPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    const text = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, 6);
    if (!text) return;
    e.preventDefault();
    const next = Array(6).fill("");
    for (let i = 0; i < text.length; i++) next[i] = text[i];
    setDigits(next);
    inputs.current[Math.min(text.length, 5)]?.focus();
  };

  const resend = async () => {
    setError(null);
    try {
      await authApi.requestSignupCode(email);
      setCooldown(COOLDOWN);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("재발송 중 오류가 발생했습니다.");
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    const codeStr = digits.join("");
    if (codeStr.length !== 6) {
      setError("6자리 인증코드를 입력해주세요.");
      return;
    }
    setCode(codeStr);
    onNext();
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <label className="text-xs text-white/60 font-medium">인증코드</label>
        <div className="flex gap-2 justify-between">
          {digits.map((d, i) => (
            <input
              key={i}
              ref={(el) => {
                inputs.current[i] = el;
              }}
              value={d}
              onChange={(e) => setDigit(i, e.target.value)}
              onKeyDown={(e) => onKeyDown(i, e)}
              onPaste={onPaste}
              inputMode="numeric"
              maxLength={1}
              className="w-12 h-14 text-center text-xl font-mono rounded-2xl bg-[var(--background-elevated-2)] border border-white/10 text-white focus:outline-none focus:border-white/30"
            />
          ))}
        </div>
        {error ? (
          <p className="text-xs text-red-300 mt-1">{error}</p>
        ) : null}
        <button
          type="button"
          onClick={resend}
          disabled={cooldown > 0}
          className="self-end text-xs text-white/50 hover:text-white disabled:hover:text-white/50 disabled:cursor-not-allowed"
        >
          {cooldown > 0 ? `재전송 (${cooldown}초)` : "인증코드 재전송"}
        </button>
      </div>

      <div className="flex gap-2 mt-2">
        <Button type="button" variant="secondary" onClick={onBack} className="flex-1">
          이전
        </Button>
        <Button type="submit" className="flex-1">
          다음
        </Button>
      </div>
    </form>
  );
}

// ---------- Step 3: 비밀번호 ----------

function PasswordStep({
  email,
  code,
  onBack,
  onComplete,
}: {
  email: string;
  code: string;
  onBack: () => void;
  onComplete: () => void;
}) {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("비밀번호는 8자 이상이어야 합니다.");
      return;
    }
    if (password !== confirm) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }

    setSubmitting(true);
    try {
      await authApi.verifySignup(email, code, password);
      onComplete();
      setTimeout(() => {
        router.push("/");
        router.refresh();
      }, 1200);
    } catch (err) {
      if (err instanceof ApiError) setError(err.message);
      else setError("가입 처리 중 오류가 발생했습니다.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-5">
      <Input
        name="password"
        type="password"
        label="비밀번호"
        autoComplete="new-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        hint="8자 이상, 영문 + 숫자 포함"
        required
      />
      <Input
        name="confirm"
        type="password"
        label="비밀번호 확인"
        autoComplete="new-password"
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        required
        error={error ?? undefined}
      />

      <div className="flex gap-2 mt-2">
        <Button type="button" variant="secondary" onClick={onBack} className="flex-1">
          이전
        </Button>
        <Button type="submit" loading={submitting} className="flex-1">
          가입 완료
        </Button>
      </div>
    </form>
  );
}

// ---------- Step 4: 완료 ----------

function DoneStep() {
  return (
    <div className="flex flex-col items-center gap-4 py-6">
      <div className="h-12 w-12 rounded-full bg-white/10 flex items-center justify-center">
        <Check className="h-6 w-6 text-white" strokeWidth={1.5} />
      </div>
      <p className="text-sm text-white/70">가입이 완료되었습니다.</p>
      <p className="text-xs text-white/40">잠시 후 홈으로 이동합니다.</p>
    </div>
  );
}
