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

export default function AdminMoviesPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [movies, setMovies] = useState<Movie[]>([]);
  const [filteredMovies, setFilteredMovies] = useState<Movie[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState<"create" | "edit">("create");
  const [selectedMovie, setSelectedMovie] = useState<Movie | null>(null);
  const [formLoading, setFormLoading] = useState(false);
  const [formError, setFormError] = useState("");

  // Form fields
  const [formTitle, setFormTitle] = useState("");
  const [formGenre, setFormGenre] = useState("");
  const [formYear, setFormYear] = useState("");
  const [formDirector, setFormDirector] = useState("");
  const [formDescription, setFormDescription] = useState("");

  // Delete confirmation
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [movieToDelete, setMovieToDelete] = useState<Movie | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchUser = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/users/me`, {
        credentials: "include",
      });

      if (!response.ok) {
        router.push("/login");
        return null;
      }

      const data = await response.json();

      // If not admin, redirect
      if (!data.is_admin) {
        router.push("/dashboard");
        return null;
      }

      setUser(data);
      return data;
    } catch {
      router.push("/login");
      return null;
    }
  }, [router, apiUrl]);

  const fetchMovies = useCallback(async () => {
    try {
      setError("");
      const response = await fetch(`${apiUrl}/movies/?skip=0&limit=100`, {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch movies");
      }

      const data = await response.json();
      setMovies(data.movies);
      setFilteredMovies(data.movies);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load movies");
    }
  }, [apiUrl]);

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      const userData = await fetchUser();
      if (userData) {
        await fetchMovies();
      }
      setIsLoading(false);
    };
    init();
  }, [fetchUser, fetchMovies]);

  // Filter movies based on search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredMovies(movies);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = movies.filter(
        (movie) =>
          movie.title.toLowerCase().includes(query) ||
          movie.director?.toLowerCase().includes(query) ||
          movie.genre?.toLowerCase().includes(query)
      );
      setFilteredMovies(filtered);
    }
  }, [searchQuery, movies]);

  const isProtectedMovie = (movieId: string): boolean => {
    const id = parseInt(movieId);
    return !isNaN(id) && id >= 1 && id <= 10;
  };

  const openCreateModal = () => {
    setModalMode("create");
    setSelectedMovie(null);
    setFormTitle("");
    setFormGenre("");
    setFormYear("");
    setFormDirector("");
    setFormDescription("");
    setFormError("");
    setShowModal(true);
  };

  const openEditModal = (movie: Movie) => {
    setModalMode("edit");
    setSelectedMovie(movie);
    setFormTitle(movie.title);
    setFormGenre(movie.genre || "");
    setFormYear(movie.year > 0 ? movie.year.toString() : "");
    setFormDirector(movie.director || "");
    setFormDescription(movie.description || "");
    setFormError("");
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
    setFormError("");
  };

  const handleSubmit = async () => {
    if (!formTitle.trim()) {
      setFormError("Title is required");
      return;
    }

    setFormLoading(true);
    setFormError("");

    try {
      const movieData = {
        title: formTitle.trim(),
        genre: formGenre.trim() || undefined,
        year: formYear ? parseInt(formYear) : undefined,
        director: formDirector.trim() || undefined,
        description: formDescription.trim() || undefined,
      };

      let response;
      if (modalMode === "create") {
        response = await fetch(`${apiUrl}/movies/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(movieData),
        });
      } else {
        response = await fetch(`${apiUrl}/movies/${selectedMovie?.movie_id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(movieData),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to save movie");
      }

      await fetchMovies();
      closeModal();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to save movie");
    } finally {
      setFormLoading(false);
    }
  };

  const openDeleteConfirm = (movie: Movie) => {
    setMovieToDelete(movie);
    setShowDeleteConfirm(true);
  };

  const closeDeleteConfirm = () => {
    setShowDeleteConfirm(false);
    setMovieToDelete(null);
  };

  const handleDelete = async () => {
    if (!movieToDelete) return;

    setDeleteLoading(true);
    try {
      const response = await fetch(`${apiUrl}/movies/${movieToDelete.movie_id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to delete movie");
      }

      await fetchMovies();
      closeDeleteConfirm();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete movie");
    } finally {
      setDeleteLoading(false);
    }
  };

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
            <div className={styles.headerLeft}>
              <button
                className={styles.backButton}
                onClick={() => router.push("/admin/dashboard")}
              >
                ← Back to Dashboard
              </button>
              <h1 className={styles.title}>Movie Management</h1>
              <p className={styles.subtitle}>
                {filteredMovies.length} movie{filteredMovies.length !== 1 ? "s" : ""}
                {searchQuery && ` matching "${searchQuery}"`}
              </p>
            </div>
            <button className={styles.addButton} onClick={openCreateModal}>
              + Add Movie
            </button>
          </div>

          {/* Search Bar */}
          <div className={styles.searchSection}>
            <div className={styles.searchBar}>
              <span className={styles.searchIcon}>🔍</span>
              <input
                type="text"
                placeholder="Search movies by title, director, or genre..."
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
          </div>

          {error && <div className={styles.error}>{error}</div>}

          {/* Movies List */}
          <div className={styles.moviesList}>
            {filteredMovies.map((movie) => (
              <div key={movie.movie_id} className={styles.movieCard}>
                <div className={styles.movieInfo}>
                  <div className={styles.movieHeader}>
                    <h3 className={styles.movieTitle}>{movie.title}</h3>
                    {isProtectedMovie(movie.movie_id) && (
                      <span className={styles.protectedBadge}>Protected</span>
                    )}
                  </div>
                  <div className={styles.movieMeta}>
                    {movie.year > 0 && (
                      <span className={styles.year}>{movie.year}</span>
                    )}
                    {movie.genre && (
                      <span className={styles.genre}>{movie.genre}</span>
                    )}
                    {movie.average_rating !== null &&
                      movie.average_rating !== undefined && (
                        <span className={styles.rating}>
                          ⭐ {movie.average_rating.toFixed(1)}
                        </span>
                      )}
                  </div>
                  {movie.director && (
                    <p className={styles.director}>Director: {movie.director}</p>
                  )}
                  {movie.description && (
                    <p className={styles.description}>{movie.description}</p>
                  )}
                </div>
                <div className={styles.movieActions}>
                  <button
                    className={styles.editButton}
                    onClick={() => openEditModal(movie)}
                  >
                    ✏️ Edit
                  </button>
                  <button
                    className={styles.deleteButton}
                    onClick={() => openDeleteConfirm(movie)}
                    disabled={isProtectedMovie(movie.movie_id)}
                    title={
                      isProtectedMovie(movie.movie_id)
                        ? "Cannot delete legacy IMDB movies"
                        : "Delete movie"
                    }
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            ))}
          </div>

          {filteredMovies.length === 0 && (
            <div className={styles.empty}>
              <p>
                {searchQuery
                  ? "No movies match your search."
                  : "No movies found."}
              </p>
            </div>
          )}
        </div>
      </main>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>{modalMode === "create" ? "Add New Movie" : "Edit Movie"}</h2>
              <button className={styles.modalClose} onClick={closeModal}>
                ×
              </button>
            </div>

            <div className={styles.modalBody}>
              <div className={styles.formGroup}>
                <label>Title *</label>
                <input
                  type="text"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="Enter movie title"
                />
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Year</label>
                  <input
                    type="number"
                    value={formYear}
                    onChange={(e) => setFormYear(e.target.value)}
                    placeholder="e.g. 2024"
                    min="1800"
                    max="2100"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Genre</label>
                  <input
                    type="text"
                    value={formGenre}
                    onChange={(e) => setFormGenre(e.target.value)}
                    placeholder="e.g. Action, Drama"
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Director</label>
                <input
                  type="text"
                  value={formDirector}
                  onChange={(e) => setFormDirector(e.target.value)}
                  placeholder="Enter director name"
                />
              </div>

              <div className={styles.formGroup}>
                <label>Description</label>
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  placeholder="Enter movie description"
                  rows={4}
                />
              </div>

              {formError && <div className={styles.formError}>{formError}</div>}
            </div>

            <div className={styles.modalFooter}>
              <button
                className={styles.cancelButton}
                onClick={closeModal}
                disabled={formLoading}
              >
                Cancel
              </button>
              <button
                className={styles.submitButton}
                onClick={handleSubmit}
                disabled={formLoading}
              >
                {formLoading
                  ? "Saving..."
                  : modalMode === "create"
                  ? "Create Movie"
                  : "Save Changes"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && movieToDelete && (
        <div className={styles.modalOverlay} onClick={closeDeleteConfirm}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Delete Movie</h2>
              <button className={styles.modalClose} onClick={closeDeleteConfirm}>
                ×
              </button>
            </div>

            <div className={styles.modalBody}>
              <p className={styles.deleteWarning}>
                Are you sure you want to delete &quot;{movieToDelete.title}&quot;?
              </p>
              <p className={styles.deleteNote}>
                This will also delete all user reviews for this movie. This action
                cannot be undone.
              </p>
            </div>

            <div className={styles.modalFooter}>
              <button
                className={styles.cancelButton}
                onClick={closeDeleteConfirm}
                disabled={deleteLoading}
              >
                Cancel
              </button>
              <button
                className={styles.deleteConfirmButton}
                onClick={handleDelete}
                disabled={deleteLoading}
              >
                {deleteLoading ? "Deleting..." : "Delete Movie"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
