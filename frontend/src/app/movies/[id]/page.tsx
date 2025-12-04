"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import Navbar from "@/components/Navbar";
import styles from "./page.module.css";

interface Movie {
  movie_id: string;
  title: string;
  genre: string;
  year: number;
  director: string;
  description: string;
  average_rating: number | null;
}

interface User {
  userid: string;
  username: string;
  email: string;
  is_admin: boolean;
}

export default function MovieDetailPage() {
  const router = useRouter();
  const params = useParams();
  const movieId = params.id as string;

  const [user, setUser] = useState<User | null>(null);
  const [movie, setMovie] = useState<Movie | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchUser = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/users/me`, {
        credentials: "include",
      });

      if (!response.ok) {
        router.push("/login");
        return null;
      }

      const data = await response.json();
      setUser(data);
      return data;
    } catch {
      router.push("/login");
      return null;
    }
  }, [router]);

  const fetchMovie = useCallback(async () => {
    try {
      setError("");
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const response = await fetch(`${apiUrl}/movies/${movieId}`, {
        credentials: "include",
      });

      if (!response.ok) {
        if (response.status === 404) {
          setError("Movie not found");
        } else {
          setError("Failed to load movie");
        }
        return;
      }

      const data: Movie = await response.json();
      setMovie(data);
    } catch {
      setError("Failed to load movie");
    }
  }, [movieId]);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      const userData = await fetchUser();
      if (userData) {
        await fetchMovie();
      }
      setIsLoading(false);
    };
    init();
  }, [fetchUser, fetchMovie]);

  const handleBackClick = () => {
    router.push("/movies");
  };

  if (isLoading) {
    return (
      <div className={styles.pageWrapper}>
        <main className={styles.main}>
          <div className={styles.loading}>Loading movie...</div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.pageWrapper}>
        <Navbar username={user?.username} isAdmin={user?.is_admin} />
        <main className={styles.main}>
          <div className={styles.container}>
            <button onClick={handleBackClick} className={styles.backButton}>
              ← Back to Movies
            </button>
            <div className={styles.error}>{error}</div>
          </div>
        </main>
      </div>
    );
  }

  if (!movie) {
    return null;
  }

  return (
    <div className={styles.pageWrapper}>
      <Navbar username={user?.username} isAdmin={user?.is_admin} />
      
      <main className={styles.main}>
        <div className={styles.container}>
          <button onClick={handleBackClick} className={styles.backButton}>
            ← Back to Movies
          </button>

          <div className={styles.movieDetail}>
            <div className={styles.posterSection}>
              <div className={styles.poster}>
                <span className={styles.posterIcon}>🎬</span>
              </div>
            </div>

            <div className={styles.infoSection}>
              <h1 className={styles.title}>{movie.title}</h1>
              
              <div className={styles.metaRow}>
                {movie.year > 0 && (
                  <span className={styles.year}>{movie.year}</span>
                )}
                {movie.genre && (
                  <span className={styles.genre}>{movie.genre}</span>
                )}
              </div>

              {movie.director && (
                <p className={styles.director}>
                  <span className={styles.label}>Director:</span> {movie.director}
                </p>
              )}

              {movie.average_rating !== null && movie.average_rating !== undefined ? (
                <div className={styles.ratingSection}>
                  <span className={styles.ratingLabel}>Community Rating</span>
                  <div className={styles.ratingDisplay}>
                    <span className={styles.star}>⭐</span>
                    <span className={styles.ratingValue}>
                      {movie.average_rating.toFixed(1)}
                    </span>
                    <span className={styles.ratingMax}>/ 5</span>
                  </div>
                </div>
              ) : (
                <div className={styles.ratingSection}>
                  <span className={styles.ratingLabel}>Community Rating</span>
                  <p className={styles.noRating}>No ratings yet</p>
                </div>
              )}

              {movie.description && (
                <div className={styles.descriptionSection}>
                  <h2 className={styles.sectionTitle}>Description</h2>
                  <p className={styles.description}>{movie.description}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
