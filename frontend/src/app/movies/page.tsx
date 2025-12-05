"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
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

// Available sort options
const SORT_OPTIONS = [
  { value: "", label: "Default" },
  { value: "title", label: "Title (A-Z)" },
  { value: "year", label: "Year (Newest)" },
];

export default function MoviesPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [movies, setMovies] = useState<Movie[]>([]);
  const [allMovies, setAllMovies] = useState<Movie[]>([]); // For extracting genres/years
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  // Search and filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("");
  const [genreFilter, setGenreFilter] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Extract unique genres from all movies
  const availableGenres = useMemo(() => {
    const genres = new Set<string>();
    allMovies.forEach((movie) => {
      if (movie.genre) {
        // Split by / or , to handle multi-genre movies
        movie.genre.split(/[\/,]/).forEach((g) => {
          const trimmed = g.trim();
          if (trimmed) genres.add(trimmed);
        });
      }
    });
    return Array.from(genres).sort();
  }, [allMovies]);

  // Extract unique years from all movies
  const availableYears = useMemo(() => {
    const years = new Set<number>();
    allMovies.forEach((movie) => {
      if (movie.year && movie.year > 0) {
        years.add(movie.year);
      }
    });
    return Array.from(years).sort((a, b) => b - a); // Newest first
  }, [allMovies]);

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

  // Fetch all movies (for getting available genres/years)
  const fetchAllMovies = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(
        `${apiUrl}/movies/?skip=0&limit=100`,
        { credentials: "include" }
      );

      if (response.ok) {
        const data: PaginatedResponse = await response.json();
        setAllMovies(data.movies);
      }
    } catch {
      // Silently fail - this is just for populating filter options
    }
  }, []);

  // Fetch movies with pagination (default view)
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

  // Search movies with filters
  const searchMovies = useCallback(async () => {
    // If no filters applied, use regular pagination
    if (!searchQuery && !sortBy && !genreFilter && !yearFilter) {
      await fetchMovies(1);
      return;
    }

    try {
      setError("");
      setIsSearching(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const params = new URLSearchParams();
      if (searchQuery) params.append("q", searchQuery);
      if (sortBy) params.append("sort_by", sortBy);
      if (genreFilter) params.append("genre", genreFilter);
      if (yearFilter) params.append("year", yearFilter);
      
      const response = await fetch(
        `${apiUrl}/movies/search?${params.toString()}`,
        { credentials: "include" }
      );

      if (!response.ok) {
        throw new Error("Failed to search movies");
      }

      const data: Movie[] = await response.json();
      setMovies(data);
      setTotal(data.length);
      setCurrentPage(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to search movies");
    } finally {
      setIsSearching(false);
    }
  }, [searchQuery, sortBy, genreFilter, yearFilter, fetchMovies]);

  // Debounced search effect
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (user) {
        searchMovies();
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [searchQuery, sortBy, genreFilter, yearFilter, user, searchMovies]);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      const userData = await fetchUser();
      if (userData) {
        await Promise.all([fetchMovies(1), fetchAllMovies()]);
      }
      setIsLoading(false);
    };
    init();
  }, [fetchUser, fetchMovies, fetchAllMovies]);

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

  const handleClearFilters = () => {
    setSearchQuery("");
    setSortBy("");
    setGenreFilter("");
    setYearFilter("");
  };

  const hasActiveFilters = searchQuery || sortBy || genreFilter || yearFilter;

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
              {hasActiveFilters 
                ? `Found ${total} movie${total !== 1 ? 's' : ''}`
                : `Browse our collection of ${total} movies`
              }
            </p>
          </div>

          {/* Search and Filter Controls */}
          <div className={styles.controls}>
            <div className={styles.searchBar}>
              <span className={styles.searchIcon}>🔍</span>
              <input
                type="text"
                placeholder="Search movies by title, director..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={styles.searchInput}
              />
              {searchQuery && (
                <button
                  className={styles.clearSearch}
                  onClick={() => setSearchQuery("")}
                >
                  ✕
                </button>
              )}
            </div>

            <div className={styles.filters}>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className={styles.filterSelect}
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    Sort: {option.label}
                  </option>
                ))}
              </select>

              <select
                value={genreFilter}
                onChange={(e) => setGenreFilter(e.target.value)}
                className={styles.filterSelect}
              >
                <option value="">All Genres</option>
                {availableGenres.map((genre) => (
                  <option key={genre} value={genre}>
                    {genre}
                  </option>
                ))}
              </select>

              <select
                value={yearFilter}
                onChange={(e) => setYearFilter(e.target.value)}
                className={styles.filterSelect}
              >
                <option value="">All Years</option>
                {availableYears.map((year) => (
                  <option key={year} value={year.toString()}>
                    {year}
                  </option>
                ))}
              </select>

              {hasActiveFilters && (
                <button
                  className={styles.clearFilters}
                  onClick={handleClearFilters}
                >
                  Clear All
                </button>
              )}
            </div>
          </div>

          {/* Active Filters Display */}
          {hasActiveFilters && (
            <div className={styles.activeFilters}>
              {searchQuery && (
                <span className={styles.filterTag}>
                  Search: &quot;{searchQuery}&quot;
                  <button onClick={() => setSearchQuery("")}>✕</button>
                </span>
              )}
              {sortBy && (
                <span className={styles.filterTag}>
                  Sort: {SORT_OPTIONS.find(o => o.value === sortBy)?.label}
                  <button onClick={() => setSortBy("")}>✕</button>
                </span>
              )}
              {genreFilter && (
                <span className={styles.filterTag}>
                  Genre: {genreFilter}
                  <button onClick={() => setGenreFilter("")}>✕</button>
                </span>
              )}
              {yearFilter && (
                <span className={styles.filterTag}>
                  Year: {yearFilter}
                  <button onClick={() => setYearFilter("")}>✕</button>
                </span>
              )}
            </div>
          )}

          {error && (
            <div className={styles.error}>{error}</div>
          )}

          {isSearching && (
            <div className={styles.searching}>Searching...</div>
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
              <p>{hasActiveFilters ? "No movies match your filters." : "No movies found."}</p>
              {hasActiveFilters && (
                <button className={styles.clearFiltersBtn} onClick={handleClearFilters}>
                  Clear Filters
                </button>
              )}
            </div>
          )}

          {/* Pagination - only show when not filtering */}
          {totalPages > 1 && !hasActiveFilters && (
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
