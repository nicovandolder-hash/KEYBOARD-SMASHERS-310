import Link from "next/link";
import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <h1 className={styles.title}>🎬 Keyboard Smashers</h1>
        <p className={styles.subtitle}>Your Movie Review Platform</p>
        
        <div className={styles.buttonGroup}>
          <Link href="/register" className={styles.primaryButton}>
            Create Account
          </Link>
          <Link href="/login" className={styles.secondaryButton}>
            Sign In
          </Link>
        </div>
      </div>
    </main>
  );
}
