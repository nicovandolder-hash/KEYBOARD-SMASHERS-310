import Link from "next/link";
import styles from "./page.module.css";

export default function LoginPage() {
  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <h1 className={styles.title}>Sign In</h1>
        <p className={styles.subtitle}>Welcome back!</p>
        
        <p className={styles.placeholder}>
          Login functionality coming soon...
        </p>
        
        <p className={styles.registerLink}>
          Don&apos;t have an account? <Link href="/register">Create one</Link>
        </p>
      </div>
    </main>
  );
}
