"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import styles from "./page.module.css";

interface Movie {
  movie_id: string;
  title: string;
  genre: string;
  year: number;
  director: string;
  description: string;
  average_rating?: number;
}

interface User {
  userid: string;
  username: string;
  email: string;
  is_admin: boolean;
}

interface PaginatedResponse {
  movies: Movie[];
  total: number;
  page: number;
  page_size: number;
}

const PAGE_SIZE = 20;

export default function MoviesPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [movies, setMovies] = useState<Movie[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const totalPages = Math.ceil(total / PAGE_SIZE);

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

  const fetchMovies = useCallback(async (page: number) => {
    try {
      setError("");
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const skip = (page - 1) * PAGE_SIZE;
      
      const response = await fetch(
        `${apiUrl}/movies/?skip=${skip}&limit=${PAGE_SIZE}`,
        { credentials: "include" }
      );

      if (!response.ok) {
        throw new Error("Failed to fetch movies");
      }

      const data: PaginatedResponse = await response.json();
      setMovies(data.movies);
      setTotal(data.total);
      setCurrentPage(page);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load movies");
    }
  }, []);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      const userData = await fetchUser();
      if (userData) {
        await fetchMovies(1);
      }
      setIsLoading(false);
    };
    init();
  }, [fetchUser, fetchMovies]);

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchMovies(newPage);
      // Scroll to top
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleMovieClick = (movieId: string) => {
    router.push(`/movies/${movieId}`);
  };

  if (isLoading) {
    return (
      <div className={styles.pageWrapper}>
        {user && <Navbar username={user.username} isAdmin={user.is_admin} />}
        <main className={styles.main}>
          <div className={styles.loading}>Loading movies...</div>
        </main>
      </div>
    );
  }

  return (
    <div className={styles.pageWrapper}>
      <Navbar username={user?.username} isAdmin={user?.is_admin} />
      
      <main className={styles.main}>
        <div className={styles.container}>
          <div className={styles.header}>
            <h1 className={styles.title}>Movies</h1>
            <p className={styles.subtitle}>
              Browse our collection of {total} movies
            </p>
          </div>

          {error && (
            <div className={styles.error}>{error}</div>
          )}

          <div className={styles.moviesGrid}>
            {movies.map((movie) => (
              <div
                key={movie.movie_id}
                className={styles.movieCard}
                onClick={() => handleMovieClick(movie.movie_id)}
              >
                <div className={styles.moviePoster}>
                  <span className={styles.posterIcon}>🎬</span>
                </div>
                <div className={styles.movieInfo}>
                  <h3 className={styles.movieTitle}>{movie.title}</h3>
                  <div className={styles.movieMeta}>
                    {movie.year > 0 && (
                      <span className={styles.year}>{movie.year}</span>
                    )}
                    {movie.genre && (
                      <span className={styles.genre}>{movie.genre}</span>
                    )}
                  </div>
                  {movie.director && (
                    <p className={styles.director}>Dir: {movie.director}</p>
                  )}
                  {movie.average_rating !== null && movie.average_rating !== undefined && (
                    <div className={styles.rating}>
                      <span className={styles.star}>⭐</span>
                      <span>{movie.average_rating.toFixed(1)}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {movies.length === 0 && !error && (
            <div className={styles.empty}>
              <p>No movies found.</p>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className={styles.pageButton}
                onClick={() => handlePageChange(1)}
                disabled={currentPage === 1}
              >
                First
              </button>
              <button
                className={styles.pageButton}
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </button>

              <div className={styles.pageInfo}>
                Page {currentPage} of {totalPages}
              </div>

              <button
                className={styles.pageButton}
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
              <button
                className={styles.pageButton}
                onClick={() => handlePageChange(totalPages)}
                disabled={currentPage === totalPages}
              >
                Last
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
