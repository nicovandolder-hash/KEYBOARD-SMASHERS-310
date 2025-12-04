"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import styles from "./page.module.css";

interface User {
  userid: string;
  username: string;
  email: string;
  is_admin: boolean;
}

export default function AdminDashboardPage() {
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
          router.push("/login");
          return;
        }

        const data = await response.json();

        // If not admin, redirect to regular dashboard
        if (!data.is_admin) {
          router.push("/dashboard");
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
        <div className={styles.loading}>Loading...</div>
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
            <div>
              <h1 className={styles.title}>Admin Dashboard</h1>
              <span className={styles.adminBadge}>Administrator</span>
            </div>
          </div>

        <div className={styles.welcomeCard}>
          <h2>Welcome, {user.username}!</h2>
          <p className={styles.email}>{user.email}</p>
        </div>

        <div className={styles.adminGrid}>
          <div className={styles.adminCard}>
            <h3>👥 User Management</h3>
            <p>Manage users, suspensions, and roles</p>
          </div>
          <div 
            className={`${styles.adminCard} ${styles.clickable}`}
            onClick={() => router.push('/admin/movies')}
          >
            <h3>🎬 Movie Management</h3>
            <p>Add, edit, or remove movies</p>
          </div>
          <div className={styles.adminCard}>
            <h3>📝 Review Moderation</h3>
            <p>Review and moderate user content</p>
          </div>
          <div className={styles.adminCard}>
            <h3>⚠️ Reports</h3>
            <p>Handle reported content</p>
          </div>
        </div>
      </div>
      </main>
    </div>
  );
}
