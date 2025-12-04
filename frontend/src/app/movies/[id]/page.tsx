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

interface Review {
  review_id: string;
  movie_id: string;
  user_id: string | null;
  username?: string;
  imdb_username?: string;
  rating: number;
  review_text: string;
  review_date: string;
}

export default function MovieDetailPage() {
  const router = useRouter();
  const params = useParams();
  const movieId = params.id as string;

  const [user, setUser] = useState<User | null>(null);
  const [movie, setMovie] = useState<Movie | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [userReview, setUserReview] = useState<Review | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalReviews, setTotalReviews] = useState(0);
  const REVIEWS_PER_PAGE = 20;
  const totalPages = Math.ceil(totalReviews / REVIEWS_PER_PAGE);
  
  // Review modal state
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [reviewRating, setReviewRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [hoverRating, setHoverRating] = useState(0);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState("");

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
      setUser(data);
      return data;
    } catch {
      router.push("/login");
      return null;
    }
  }, [router, apiUrl]);

  const fetchMovie = useCallback(async () => {
    try {
      setError("");
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
  }, [movieId, apiUrl]);

  const fetchReviews = useCallback(async (currentUserId?: string, currentUsername?: string, page = 1) => {
    try {
      const skip = (page - 1) * REVIEWS_PER_PAGE;
      
      // Fetch movie reviews with pagination
      const response = await fetch(`${apiUrl}/reviews/movie/${movieId}?skip=${skip}&limit=${REVIEWS_PER_PAGE}`, {
        credentials: "include",
      });

      let reviewsList: Review[] = [];
      let myReview: Review | null = null;

      if (response.ok) {
        const data = await response.json();
        reviewsList = data.reviews || [];
        setTotalReviews(data.total || 0);
      }

      // If user is logged in, also fetch their review for this movie
      if (currentUserId) {
        try {
          const userReviewsResponse = await fetch(`${apiUrl}/reviews/user/${currentUserId}?limit=100`, {
            credentials: "include",
          });
          if (userReviewsResponse.ok) {
            const userReviewsData = await userReviewsResponse.json();
            const userReviews: Review[] = userReviewsData.reviews || [];
            // Find user's review for this movie and add username
            const foundReview = userReviews.find((r: Review) => r.movie_id === movieId);
            if (foundReview) {
              myReview = { ...foundReview, username: currentUsername };
            }
            setUserReview(myReview);
            
            // On first page, add user's review at top if not already present
            if (page === 1 && myReview && !reviewsList.find((r: Review) => r.review_id === myReview!.review_id)) {
              reviewsList.unshift(myReview);
            }
          }
        } catch {
          // Ignore user review fetch errors
        }
      }
      
      // Sort by date descending (most recent first)
      // Handle both ISO dates (2025-11-20T...) and text dates (4 May 2019)
      reviewsList = reviewsList.sort((a, b) => {
        const dateA = new Date(a.review_date).getTime();
        const dateB = new Date(b.review_date).getTime();
        // If parsing fails (NaN), treat as old date
        const safeA = isNaN(dateA) ? 0 : dateA;
        const safeB = isNaN(dateB) ? 0 : dateB;
        return safeB - safeA;
      });
      
      setReviews(reviewsList);
      setCurrentPage(page);
    } catch {
      // Ignore review fetch errors
    }
  }, [movieId, apiUrl]);

  const handleReviewPageChange = (page: number) => {
    fetchReviews(user?.userid, user?.username, page);
  };

  useEffect(() => {
    const init = async () => {
      setIsLoading(true);
      const userData = await fetchUser();
      if (userData) {
        await fetchMovie();
        await fetchReviews(userData.userid, userData.username);
      }
      setIsLoading(false);
    };
    init();
  }, [fetchUser, fetchMovie, fetchReviews]);

  const handleBackClick = () => {
    router.push("/movies");
  };

  const openWriteReview = () => {
    setIsEditing(false);
    setReviewRating(0);
    setReviewText("");
    setSubmitError("");
    setShowReviewModal(true);
  };

  const openEditReview = () => {
    if (userReview) {
      setIsEditing(true);
      setReviewRating(userReview.rating);
      setReviewText(userReview.review_text);
      setSubmitError("");
      setShowReviewModal(true);
    }
  };

  const closeModal = () => {
    setShowReviewModal(false);
    setSubmitError("");
  };

  const handleSubmitReview = async () => {
    if (reviewRating === 0) {
      setSubmitError("Please select a rating");
      return;
    }
    if (reviewText.trim().length === 0) {
      setSubmitError("Please write a review");
      return;
    }
    if (reviewText.length > 250) {
      setSubmitError("Review must be 250 characters or less");
      return;
    }

    setSubmitLoading(true);
    setSubmitError("");

    try {
      if (isEditing && userReview) {
        // Update existing review
        const response = await fetch(`${apiUrl}/reviews/${userReview.review_id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            rating: reviewRating,
            review_text: reviewText.trim(),
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to update review");
        }
      } else {
        // Create new review
        const response = await fetch(`${apiUrl}/reviews/`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            movie_id: movieId,
            rating: reviewRating,
            review_text: reviewText.trim(),
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || "Failed to submit review");
        }
      }

      // Refresh data
      await fetchMovie();
      await fetchReviews(user?.userid, user?.username);
      closeModal();
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleDeleteReview = async () => {
    if (!userReview) return;
    
    if (!confirm("Are you sure you want to delete your review?")) return;

    setSubmitLoading(true);
    try {
      const response = await fetch(`${apiUrl}/reviews/${userReview.review_id}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to delete review");
      }

      // Refresh data
      await fetchMovie();
      await fetchReviews(user?.userid, user?.username);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete review");
    } finally {
      setSubmitLoading(false);
    }
  };

  const renderStars = (rating: number, interactive = false) => {
    return (
      <div className={styles.starsContainer}>
        {[1, 2, 3, 4, 5].map((star) => (
          <span
            key={star}
            className={`${styles.starIcon} ${
              star <= (interactive ? (hoverRating || reviewRating) : rating)
                ? styles.starFilled
                : styles.starEmpty
            } ${interactive ? styles.starInteractive : ""}`}
            onClick={interactive ? () => setReviewRating(star) : undefined}
            onMouseEnter={interactive ? () => setHoverRating(star) : undefined}
            onMouseLeave={interactive ? () => setHoverRating(0) : undefined}
          >
            ★
          </span>
        ))}
      </div>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
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

          {/* Your Review Section */}
          <div className={styles.yourReviewSection}>
            <h2 className={styles.sectionTitle}>Your Review</h2>
            {userReview ? (
              <div className={styles.userReviewCard}>
                <div className={styles.reviewHeader}>
                  {renderStars(userReview.rating)}
                  <span className={styles.reviewDate}>{formatDate(userReview.review_date)}</span>
                </div>
                <p className={styles.reviewText}>{userReview.review_text}</p>
                <div className={styles.reviewActions}>
                  <button 
                    className={styles.editButton} 
                    onClick={openEditReview}
                    disabled={submitLoading}
                  >
                    ✏️ Edit
                  </button>
                  <button 
                    className={styles.deleteButton} 
                    onClick={handleDeleteReview}
                    disabled={submitLoading}
                  >
                    🗑️ Delete
                  </button>
                </div>
              </div>
            ) : (
              <div className={styles.noReviewCard}>
                <p>You haven&apos;t reviewed this movie yet.</p>
                <button className={styles.writeReviewButton} onClick={openWriteReview}>
                  ✍️ Write a Review
                </button>
              </div>
            )}
          </div>

          {/* All Reviews Section */}
          <div className={styles.reviewsSection}>
            <h2 className={styles.sectionTitle}>
              Reviews ({totalReviews})
            </h2>
            {reviews.length === 0 ? (
              <p className={styles.noReviews}>No reviews yet. Be the first to review!</p>
            ) : (
              <>
                <div className={styles.reviewsList}>
                  {reviews.map((review) => (
                    <div 
                      key={review.review_id} 
                      className={`${styles.reviewCard} ${review.user_id === user?.userid ? styles.ownReview : ""}`}
                    >
                      <div className={styles.reviewHeader}>
                        <span className={styles.reviewAuthor}>
                          {review.username || review.imdb_username || "Anonymous"}
                        </span>
                        {renderStars(review.rating)}
                        <span className={styles.reviewDate}>{formatDate(review.review_date)}</span>
                      </div>
                      <p className={styles.reviewText}>{review.review_text}</p>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className={styles.pagination}>
                    <button
                      className={styles.pageButton}
                      onClick={() => handleReviewPageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </button>

                    <span className={styles.pageInfo}>
                      Page {currentPage} of {totalPages}
                    </span>

                    <button
                      className={styles.pageButton}
                      onClick={() => handleReviewPageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </main>

      {/* Review Modal */}
      {showReviewModal && (
        <div className={styles.modalOverlay} onClick={closeModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>{isEditing ? "Edit Your Review" : "Write a Review"}</h2>
              <button className={styles.modalClose} onClick={closeModal}>×</button>
            </div>
            
            <div className={styles.modalBody}>
              <div className={styles.ratingInput}>
                <label>Your Rating</label>
                {renderStars(reviewRating, true)}
              </div>
              
              <div className={styles.textInput}>
                <label>Your Review</label>
                <textarea
                  value={reviewText}
                  onChange={(e) => setReviewText(e.target.value)}
                  placeholder="Share your thoughts about this movie..."
                  maxLength={250}
                  rows={4}
                />
                <span className={styles.charCount}>
                  {reviewText.length}/250
                </span>
              </div>

              {submitError && (
                <div className={styles.submitError}>{submitError}</div>
              )}
            </div>

            <div className={styles.modalFooter}>
              <button 
                className={styles.cancelButton} 
                onClick={closeModal}
                disabled={submitLoading}
              >
                Cancel
              </button>
              <button 
                className={styles.submitButton} 
                onClick={handleSubmitReview}
                disabled={submitLoading}
              >
                {submitLoading ? "Submitting..." : isEditing ? "Update Review" : "Submit Review"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
