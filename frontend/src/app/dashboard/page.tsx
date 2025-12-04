"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
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

  const handleLogout = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/users/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Ignore errors
    }
    router.push("/login");
  };

  if (isLoading) {
    return (
      <main className={styles.main}>
        <div className={styles.loading}>Loading...</div>
      </main>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Dashboard</h1>
          <button onClick={handleLogout} className={styles.logoutButton}>
            Sign Out
          </button>
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
  );
}
