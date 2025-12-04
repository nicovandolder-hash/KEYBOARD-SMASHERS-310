"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./page.module.css";

interface FormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
}

interface FormErrors {
  username?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

export default function RegisterPage() {
  const router = useRouter();
  const [formData, setFormData] = useState<FormData>({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string>("");

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {};

    // Username validation
    if (!formData.username.trim()) {
      newErrors.username = "Username is required";
    } else if (formData.username.length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!emailRegex.test(formData.email)) {
      newErrors.email = "Please enter a valid email address";
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    } else if (!/[0-9]/.test(formData.password)) {
      newErrors.password = "Password must contain at least one digit";
    } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
      newErrors.password = "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)";
    } else if (!/[A-Z]/.test(formData.password)) {
      newErrors.password = "Password must contain at least one uppercase letter";
    } else if (!/[a-z]/.test(formData.password)) {
      newErrors.password = "Password must contain at least one lowercase letter";
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    
    // Clear error when user starts typing
    if (errors[name as keyof FormErrors]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
    setServerError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setServerError("");
    setSuccessMessage("");

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/users/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password,
        }),
      });

      if (!response.ok) {
        // Handle backend errors (duplicate email/username, validation errors)
        const data = await response.json();
        throw new Error(data.detail || "Registration failed");
      }

      // Success!
      setSuccessMessage("Account created successfully! Redirecting to login...");
      
      // Redirect to login page after a short delay
      setTimeout(() => {
        router.push("/login");
      }, 2000);

    } catch (error) {
      if (error instanceof TypeError && error.message === "Failed to fetch") {
        setServerError("Unable to connect to server. Please make sure the backend is running.");
      } else if (error instanceof Error) {
        setServerError(error.message);
      } else {
        setServerError("An unexpected error occurred. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className={styles.main}>
      <div className={styles.container}>
        <h1 className={styles.title}>Create Account</h1>
        <p className={styles.subtitle}>Join Keyboard Smashers today</p>

        {successMessage && (
          <div className={styles.successMessage}>{successMessage}</div>
        )}

        {serverError && (
          <div className={styles.errorMessage}>{serverError}</div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label htmlFor="username" className={styles.label}>
              Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              className={`${styles.input} ${errors.username ? styles.inputError : ""}`}
              placeholder="Enter your username"
              disabled={isLoading}
            />
            {errors.username && (
              <span className={styles.fieldError}>{errors.username}</span>
            )}
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="email" className={styles.label}>
              Email
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className={`${styles.input} ${errors.email ? styles.inputError : ""}`}
              placeholder="Enter your email"
              disabled={isLoading}
            />
            {errors.email && (
              <span className={styles.fieldError}>{errors.email}</span>
            )}
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password" className={styles.label}>
              Password
            </label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              className={`${styles.input} ${errors.password ? styles.inputError : ""}`}
              placeholder="Enter your password"
              disabled={isLoading}
            />
            {errors.password && (
              <span className={styles.fieldError}>{errors.password}</span>
            )}
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="confirmPassword" className={styles.label}>
              Confirm Password
            </label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              className={`${styles.input} ${errors.confirmPassword ? styles.inputError : ""}`}
              placeholder="Confirm your password"
              disabled={isLoading}
            />
            {errors.confirmPassword && (
              <span className={styles.fieldError}>{errors.confirmPassword}</span>
            )}
          </div>

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isLoading}
          >
            {isLoading ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <p className={styles.loginLink}>
          Already have an account? <Link href="/login">Sign in</Link>
        </p>
      </div>
    </main>
  );
}
