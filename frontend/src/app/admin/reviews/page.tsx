"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import styles from "./page.module.css";

interface User {
  userid: string;
  username: string;
  email: string;
  is_admin: boolean;
}

interface PublicUser {
  userid: string;
  username: string;
  total_reviews: number;
}

interface Review {
  review_id: string;
  movie_id: string;
  user_id: string | null;
  imdb_username: string | null;
  rating: number;
  review_text: string;
  review_date: string;
}

interface Movie {
  movie_id: string;
  title: string;
  year: number;
  genre: string;
}

export default function AdminReviewsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<PublicUser[]>([]);
  const [selectedUser, setSelectedUser] = useState<PublicUser | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [movies, setMovies] = useState<Record<string, Movie>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(false);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  
  // User search/pagination
  const [userSearchQuery, setUserSearchQuery] = useState("");
  const [userPage, setUserPage] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const USERS_PER_PAGE = 20;

  // Review pagination
  const [reviewPage, setReviewPage] = useState(1);
  const [totalReviews, setTotalReviews] = useState(0);
  const REVIEWS_PER_PAGE = 10;

  // Delete state
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const offset = (userPage - 1) * USERS_PER_PAGE;
      const url = `${apiUrl}/users/search/users?q=${encodeURIComponent(userSearchQuery)}&limit=${USERS_PER_PAGE}&offset=${offset}`;
      
      const response = await fetch(url, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        // Show all users - total_reviews in user record may be out of sync
        // Admin can click on user to see their actual reviews
        setUsers(data.users || []);
        setTotalUsers(data.total || 0);
      }
    } catch {
      // Ignore errors
    } finally {
      setUsersLoading(false);
    }
  }, [apiUrl, userSearchQuery, userPage]);

  const fetchReviewsForUser = useCallback(async (userId: string) => {
    setReviewsLoading(true);
    try {
      const skip = (reviewPage - 1) * REVIEWS_PER_PAGE;
      const url = `${apiUrl}/reviews/user/${userId}?skip=${skip}&limit=${REVIEWS_PER_PAGE}`;
      
      const response = await fetch(url, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        // Filter out IMDB reviews (they have imdb_username and no user_id)
        const userReviews = (data.reviews || []).filter((r: Review) => r.user_id && !r.imdb_username);
        setReviews(userReviews);
        setTotalReviews(data.total || 0);

        // Fetch movie details
        const movieIds = [...new Set(userReviews.map((r: Review) => r.movie_id))];
        
        setMovies(prevMovies => {
          const movieMap: Record<string, Movie> = { ...prevMovies };
          
          // Fetch missing movies
          movieIds.forEach(async (movieId) => {
            if (!movieMap[movieId as string]) {
              try {
                const movieRes = await fetch(`${apiUrl}/movies/${movieId}`, {
                  credentials: "include",
                });
                if (movieRes.ok) {
                  const movieData = await movieRes.json();
                  setMovies(prev => ({ ...prev, [movieId as string]: movieData }));
                }
              } catch {
                // Ignore movie fetch errors
              }
            }
          });
          
          return movieMap;
        });
      }
    } catch {
      // Ignore errors
    } finally {
      setReviewsLoading(false);
    }
  }, [apiUrl, reviewPage]);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const response = await fetch(`${apiUrl}/users/me`, {
          credentials: "include",
        });

        if (!response.ok) {
          router.push("/login");
          return;
        }

        const data = await response.json();

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
  }, [router, apiUrl]);

  useEffect(() => {
    if (user) {
      fetchUsers();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, userPage]);

  useEffect(() => {
    if (selectedUser) {
      fetchReviewsForUser(selectedUser.userid);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUser, reviewPage]);

  const handleUserSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setUserPage(1);
    setSelectedUser(null);
    setReviews([]);
    fetchUsers();
  };

  const handleSelectUser = (u: PublicUser) => {
    setSelectedUser(u);
    setReviewPage(1);
  };

  const handleDeleteReview = async (reviewId: string) => {
    setDeleteLoading(reviewId);
    try {
      const response = await fetch(`${apiUrl}/reviews/${reviewId}/admin`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.ok) {
        // Remove from local state
        setReviews(prev => prev.filter(r => r.review_id !== reviewId));
        setTotalReviews(prev => prev - 1);
        
        // Update user's review count in the list
        if (selectedUser) {
          setUsers(prev => prev.map(u => 
            u.userid === selectedUser.userid 
              ? { ...u, total_reviews: u.total_reviews - 1 }
              : u
          ));
          setSelectedUser(prev => prev ? { ...prev, total_reviews: prev.total_reviews - 1 } : null);
        }
      }
    } catch {
      // Ignore errors
    } finally {
      setDeleteLoading(null);
      setConfirmDelete(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const renderStars = (rating: number) => {
    return "⭐".repeat(rating) + "☆".repeat(5 - rating);
  };

  const totalUserPages = Math.ceil(totalUsers / USERS_PER_PAGE);
  const totalReviewPages = Math.ceil(totalReviews / REVIEWS_PER_PAGE);

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
            <button onClick={() => router.push("/admin/dashboard")} className={styles.backButton}>
              ← Back to Admin Dashboard
            </button>
            <h1 className={styles.title}>📝 Review Management</h1>
            <p className={styles.subtitle}>View and delete user reviews</p>
          </div>

          <div className={styles.layout}>
            {/* Users Panel */}
            <div className={styles.usersPanel}>
              <h2 className={styles.panelTitle}>Users</h2>
              
              {/* Search Bar */}
              <form onSubmit={handleUserSearch} className={styles.searchForm}>
                <input
                  type="text"
                  value={userSearchQuery}
                  onChange={(e) => setUserSearchQuery(e.target.value)}
                  placeholder="Search by username..."
                  className={styles.searchInput}
                />
                <button type="submit" className={styles.searchButton}>
                  🔍
                </button>
              </form>

              {/* Users List */}
              {usersLoading ? (
                <div className={styles.loadingSmall}>Loading users...</div>
              ) : users.length === 0 ? (
                <div className={styles.emptyState}>No users with reviews found</div>
              ) : (
                <>
                  <div className={styles.usersList}>
                    {users.map((u) => (
                      <div
                        key={u.userid}
                        className={`${styles.userCard} ${selectedUser?.userid === u.userid ? styles.selected : ""}`}
                        onClick={() => handleSelectUser(u)}
                      >
                        <div className={styles.userAvatar}>
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <div className={styles.userInfo}>
                          <span className={styles.userName}>{u.username}</span>
                          <span className={styles.userReviews}>Click to view reviews</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* User Pagination */}
                  {totalUserPages > 1 && (
                    <div className={styles.pagination}>
                      <button
                        className={styles.pageButton}
                        onClick={() => setUserPage(prev => prev - 1)}
                        disabled={userPage === 1}
                      >
                        ←
                      </button>
                      <span className={styles.pageInfo}>
                        {userPage} / {totalUserPages}
                      </span>
                      <button
                        className={styles.pageButton}
                        onClick={() => setUserPage(prev => prev + 1)}
                        disabled={userPage === totalUserPages}
                      >
                        →
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Reviews Panel */}
            <div className={styles.reviewsPanel}>
              {selectedUser ? (
                <>
                  <div className={styles.reviewsPanelHeader}>
                    <h2 className={styles.panelTitle}>
                      Reviews by {selectedUser.username}
                    </h2>
                    <span className={styles.reviewCount}>
                      {totalReviews} total
                    </span>
                  </div>

                  {reviewsLoading ? (
                    <div className={styles.loadingSmall}>Loading reviews...</div>
                  ) : reviews.length === 0 ? (
                    <div className={styles.emptyState}>No user reviews found</div>
                  ) : (
                    <>
                      <div className={styles.reviewsList}>
                        {reviews.map((review) => (
                          <div key={review.review_id} className={styles.reviewCard}>
                            <div className={styles.reviewHeader}>
                              <span 
                                className={styles.movieTitle}
                                onClick={() => router.push(`/movies/${review.movie_id}`)}
                              >
                                {movies[review.movie_id]?.title || "Loading..."}
                              </span>
                              <span className={styles.reviewRating}>
                                {renderStars(review.rating)}
                              </span>
                              <span className={styles.reviewDate}>
                                {formatDate(review.review_date)}
                              </span>
                            </div>
                            <p className={styles.reviewText}>{review.review_text}</p>
                            
                            <div className={styles.reviewActions}>
                              {confirmDelete === review.review_id ? (
                                <div className={styles.confirmGroup}>
                                  <span>Delete this review?</span>
                                  <button
                                    className={styles.confirmYes}
                                    onClick={() => handleDeleteReview(review.review_id)}
                                    disabled={deleteLoading === review.review_id}
                                  >
                                    {deleteLoading === review.review_id ? "..." : "Yes"}
                                  </button>
                                  <button
                                    className={styles.confirmNo}
                                    onClick={() => setConfirmDelete(null)}
                                  >
                                    No
                                  </button>
                                </div>
                              ) : (
                                <button
                                  className={styles.deleteButton}
                                  onClick={() => setConfirmDelete(review.review_id)}
                                  disabled={deleteLoading === review.review_id}
                                >
                                  🗑️ Delete
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>

                      {/* Review Pagination */}
                      {totalReviewPages > 1 && (
                        <div className={styles.pagination}>
                          <button
                            className={styles.pageButton}
                            onClick={() => setReviewPage(prev => prev - 1)}
                            disabled={reviewPage === 1}
                          >
                            Previous
                          </button>
                          <span className={styles.pageInfo}>
                            Page {reviewPage} of {totalReviewPages}
                          </span>
                          <button
                            className={styles.pageButton}
                            onClick={() => setReviewPage(prev => prev + 1)}
                            disabled={reviewPage === totalReviewPages}
                          >
                            Next
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </>
              ) : (
                <div className={styles.selectPrompt}>
                  <div className={styles.selectIcon}>👈</div>
                  <p>Select a user to view their reviews</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
