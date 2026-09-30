"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./lib/auth";

export default function HomePage() {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    router.replace(user ? user.inicio : "/login");
  }, [ready, user, router]);

  return <p className="center-msg">Abrindo…</p>;
}
