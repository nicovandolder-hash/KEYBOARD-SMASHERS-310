"use client";

import { useRouter, usePathname } from "next/navigation";
import styles from "./Navbar.module.css";

interface NavbarProps {
  username?: string;
  isAdmin?: boolean;
}

export default function Navbar({ username, isAdmin }: NavbarProps) {
  const router = useRouter();
  const pathname = usePathname();

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

  const navItems = isAdmin
    ? [
        { href: "/admin/dashboard", label: "Dashboard" },
        { href: "/movies", label: "Movies" },
      ]
    : [
        { href: "/dashboard", label: "Dashboard" },
        { href: "/movies", label: "Movies" },
      ];

  return (
    <nav className={styles.navbar}>
      <div className={styles.navContent}>
        <div className={styles.logo} onClick={() => router.push(isAdmin ? "/admin/dashboard" : "/dashboard")}>
          🎬 MovieHub
        </div>
        
        <div className={styles.navLinks}>
          {navItems.map((item) => (
            <button
              key={item.href}
              onClick={() => router.push(item.href)}
              className={`${styles.navLink} ${pathname === item.href ? styles.active : ""}`}
            >
              {item.label}
            </button>
          ))}
        </div>

        <div className={styles.userSection}>
          {username && <span className={styles.username}>{username}</span>}
          {isAdmin && <span className={styles.adminBadge}>Admin</span>}
          <button onClick={handleLogout} className={styles.logoutButton}>
            Sign Out
          </button>
        </div>
      </div>
    </nav>
  );
}
