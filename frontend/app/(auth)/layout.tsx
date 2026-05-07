import Logo from "@/components/Logo";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-[400px]">
        <div className="mb-10 flex justify-center">
          <Logo className="text-3xl" />
        </div>
        {children}
      </div>
    </main>
  );
}
