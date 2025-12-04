"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import styles from "./page.module.css";

interface User {
  userid: string;
  username: string;
  email: string;
  reputation: number;
  is_admin: boolean;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const response = await fetch(`${apiUrl}/users/me`, {
          credentials: "include",
        });

        if (!response.ok) {
          // Not logged in, redirect to login
          router.push("/login");
          return;
        }

        const data = await response.json();
        
        // If admin, redirect to admin dashboard
        if (data.is_admin) {
          router.push("/admin/dashboard");
          return;
        }

        setUser(data);
      } catch {
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, [router]);

  if (isLoading) {
    return (
      <div className={styles.pageWrapper}>
        <main className={styles.main}>
          <div className={styles.loading}>Loading...</div>
        </main>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className={styles.pageWrapper}>
      <Navbar username={user.username} isAdmin={user.is_admin} />
      <main className={styles.main}>
        <div className={styles.container}>
          <div className={styles.header}>
            <h1 className={styles.title}>Dashboard</h1>
          </div>

          <div className={styles.welcomeCard}>
            <h2>Welcome, {user.username}!</h2>
            <p className={styles.email}>{user.email}</p>
          </div>

          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <span className={styles.statValue}>{user.reputation}</span>
              <span className={styles.statLabel}>Reputation</span>
            </div>
          </div>

          <div className={styles.placeholder}>
            <p>🎬 Your movie reviews and activity will appear here.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
