import type { Metadata } from "next";
import "./globals.css";
import AuthGate from "@/components/AuthGate";
import { VoiceProvider } from "@/components/providers/VoiceProvider";

export const metadata: Metadata = {
  title: "StudyNest · 视频自习室",
  description: "在 StudyNest，和小悟一起学习、聊天、专注、记录成长",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <div className="mx-auto flex min-h-dvh w-full max-w-[480px] flex-col">
          <VoiceProvider>
            <AuthGate>{children}</AuthGate>
          </VoiceProvider>
        </div>
      </body>
    </html>
  );
}
