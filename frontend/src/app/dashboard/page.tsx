"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import styles from "./page.module.css";

interface User {
  userid: string;
  username: string;
  email: string;
  is_admin: boolean;
  favorites: string[];
  total_reviews: number;
}

interface PublicUser {
  userid: string;
  username: string;
  total_reviews: number;
  favorites: string[];
}

interface Review {
  review_id: string;
  movie_id: string;
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

interface Penalty {
  penalty_id: string;
  user_id: string;
  reason: string;
  penalty_type: string;
  is_active: boolean;
  issued_at: string;
  expires_at: string | null;
}

interface BlockedUser {
  userid: string;
  username: string;
}

interface Notification {
  timestamp: string;
  event_type: string;
  data: {
    message?: string;
    follower_id?: string;
    follower_username?: string;
  };
  review_id?: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [favoriteMovies, setFavoriteMovies] = useState<Movie[]>([]);
  const [penalties, setPenalties] = useState<Penalty[]>([]);
  const [followers, setFollowers] = useState<PublicUser[]>([]);
  const [following, setFollowing] = useState<PublicUser[]>([]);
  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [reviewMovies, setReviewMovies] = useState<Record<string, Movie>>({});
  const [showBlockedModal, setShowBlockedModal] = useState(false);
  const [followerCount, setFollowerCount] = useState(0);
  const [followingCount, setFollowingCount] = useState(0);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchBlockedUsers = async () => {
    try {
      const response = await fetch(`${apiUrl}/users/me/blocked`, {
        credentials: "include",
      });
      if (response.ok) {
        const data = await response.json();
        setBlockedUsers(data.blocked_users || []);
      }
    } catch {
      // Ignore errors
    }
  };

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Fetch current user
        const userResponse = await fetch(`${apiUrl}/users/me`, {
          credentials: "include",
        });

        if (!userResponse.ok) {
          router.push("/login");
          return;
        }

        const userData = await userResponse.json();
        
        // If admin, redirect to admin dashboard
        if (userData.is_admin) {
          router.push("/admin/dashboard");
          return;
        }

        setUser(userData);

        // Fetch all dashboard data in parallel
        const [reviewsRes, penaltiesRes, followersRes, followingRes, notificationsRes] = await Promise.all([
          fetch(`${apiUrl}/reviews/user/${userData.userid}?limit=50`, { credentials: "include" }),
          fetch(`${apiUrl}/penalties/my-penalties`, { credentials: "include" }),
          fetch(`${apiUrl}/users/${userData.userid}/followers?limit=100`, { credentials: "include" }),
          fetch(`${apiUrl}/users/${userData.userid}/following?limit=100`, { credentials: "include" }),
          fetch(`${apiUrl}/users/me/notifications?limit=20`, { credentials: "include" }),
        ]);

        // Process reviews
        if (reviewsRes.ok) {
          const reviewsData = await reviewsRes.json();
          setReviews(reviewsData.reviews || []);
          
          // Fetch movie details for each review
          const movieIds = [...new Set(reviewsData.reviews?.map((r: Review) => r.movie_id) || [])];
          const movieDetails: Record<string, Movie> = {};
          await Promise.all(
            movieIds.map(async (movieId) => {
              try {
                const movieResponse = await fetch(`${apiUrl}/movies/${movieId}`, {
                  credentials: "include",
                });
                if (movieResponse.ok) {
                  movieDetails[movieId as string] = await movieResponse.json();
                }
              } catch {
                // Skip failed movie fetches
              }
            })
          );
          setReviewMovies(movieDetails);
        }

        // Process penalties
        if (penaltiesRes.ok) {
          const penaltiesData = await penaltiesRes.json();
          setPenalties(penaltiesData.penalties || []);
        }

        // Process followers
        if (followersRes.ok) {
          const followersData = await followersRes.json();
          setFollowers(followersData.followers || []);
          setFollowerCount(followersData.total || 0);
        }

        // Process following
        if (followingRes.ok) {
          const followingData = await followingRes.json();
          setFollowing(followingData.following || []);
          setFollowingCount(followingData.total || 0);
        }

        // Process notifications
        if (notificationsRes.ok) {
          const notificationsData = await notificationsRes.json();
          setNotifications(notificationsData.notifications || []);
          setUnreadCount(notificationsData.unread || 0);
        }

        // Fetch blocked users
        await fetchBlockedUsers();

        // Fetch favorite movies details
        if (userData.favorites && userData.favorites.length > 0) {
          const favMovies: Movie[] = [];
          await Promise.all(
            userData.favorites.map(async (movieId: string) => {
              try {
                const movieResponse = await fetch(`${apiUrl}/movies/${movieId}`, {
                  credentials: "include",
                });
                if (movieResponse.ok) {
                  favMovies.push(await movieResponse.json());
                }
              } catch {
                // Skip failed fetches
              }
            })
          );
          setFavoriteMovies(favMovies);
        }

      } catch {
        router.push("/login");
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router, apiUrl]);

  const handleUnblock = async (userId: string) => {
    try {
      const response = await fetch(`${apiUrl}/users/${userId}/block`, {
        method: "DELETE",
        credentials: "include",
      });
      if (response.ok) {
        setBlockedUsers((prev) => prev.filter((u) => u.userid !== userId));
      }
    } catch {
      // Ignore errors
    }
  };

  const renderStars = (rating: number) => {
    return "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
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
          <div className={styles.loading}>Loading...</div>
        </main>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const activePenalties = penalties.filter((p) => p.is_active);

  return (
    <div className={styles.pageWrapper}>
      <Navbar username={user.username} isAdmin={user.is_admin} />
      <main className={styles.main}>
        <div className={styles.container}>
          <div className={styles.header}>
            <h1 className={styles.title}>Dashboard</h1>
          </div>

          {/* Active Penalties Warning */}
          {activePenalties.length > 0 && (
            <div className={styles.penaltyWarning}>
              <div className={styles.penaltyWarningHeader}>
                <span className={styles.warningIcon}>⚠️</span>
                <h3>Active Penalties</h3>
              </div>
              {activePenalties.map((penalty) => (
                <div key={penalty.penalty_id} className={styles.penaltyItem}>
                  <div className={styles.penaltyType}>{penalty.penalty_type}</div>
                  <p className={styles.penaltyReason}>{penalty.reason}</p>
                  {penalty.expires_at && (
                    <p className={styles.penaltyExpires}>
                      Expires: {formatDate(penalty.expires_at)}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          <div className={styles.welcomeCard}>
            <h2>Welcome, {user.username}!</h2>
            <p className={styles.email}>{user.email}</p>
          </div>

          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <span className={styles.statValue}>{reviews.length}</span>
              <span className={styles.statLabel}>Reviews</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statValue}>{favoriteMovies.length}</span>
              <span className={styles.statLabel}>Favorites</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statValue}>{followerCount}</span>
              <span className={styles.statLabel}>Followers</span>
            </div>
            <div className={styles.statCard}>
              <span className={styles.statValue}>{followingCount}</span>
              <span className={styles.statLabel}>Following</span>
            </div>
            <div 
              className={`${styles.statCard} ${styles.clickable}`}
              onClick={() => setShowBlockedModal(true)}
            >
              <span className={styles.statValue}>{blockedUsers.length}</span>
              <span className={styles.statLabel}>Blocked</span>
            </div>
          </div>

          {/* Followers & Following Section */}
          <div className={styles.socialGrid}>
            {/* Followers */}
            <section className={styles.socialSection}>
              <h2 className={styles.sectionTitle}>👥 Followers</h2>
              {followers.length === 0 ? (
                <div className={styles.emptyStateSmall}>
                  <p>No followers yet</p>
                </div>
              ) : (
                <div className={styles.userList}>
                  {followers.slice(0, 5).map((follower) => (
                    <div 
                      key={follower.userid} 
                      className={styles.userCard}
                      onClick={() => router.push(`/users/${follower.userid}`)}
                    >
                      <div className={styles.userAvatar}>
                        {follower.username.charAt(0).toUpperCase()}
                      </div>
                      <div className={styles.userInfo}>
                        <span className={styles.userName}>{follower.username}</span>
                        <span className={styles.userMeta}>{follower.total_reviews} reviews</span>
                      </div>
                    </div>
                  ))}
                  {followers.length > 5 && (
                    <p className={styles.moreText}>+ {followers.length - 5} more</p>
                  )}
                </div>
              )}
            </section>

            {/* Following */}
            <section className={styles.socialSection}>
              <h2 className={styles.sectionTitle}>➡️ Following</h2>
              {following.length === 0 ? (
                <div className={styles.emptyStateSmall}>
                  <p>Not following anyone</p>
                </div>
              ) : (
                <div className={styles.userList}>
                  {following.slice(0, 5).map((followee) => (
                    <div 
                      key={followee.userid} 
                      className={styles.userCard}
                      onClick={() => router.push(`/users/${followee.userid}`)}
                    >
                      <div className={styles.userAvatar}>
                        {followee.username.charAt(0).toUpperCase()}
                      </div>
                      <div className={styles.userInfo}>
                        <span className={styles.userName}>{followee.username}</span>
                        <span className={styles.userMeta}>{followee.total_reviews} reviews</span>
                      </div>
                    </div>
                  ))}
                  {following.length > 5 && (
                    <p className={styles.moreText}>+ {following.length - 5} more</p>
                  )}
                </div>
              )}
            </section>
          </div>

          {/* Notifications Section */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              🔔 Notifications
              {unreadCount > 0 && (
                <span className={styles.notificationBadge}>{unreadCount}</span>
              )}
            </h2>
            {notifications.length === 0 ? (
              <div className={styles.emptyState}>
                <p>No notifications yet</p>
              </div>
            ) : (
              <div className={styles.notificationsList}>
                {notifications.slice(0, 10).map((notification, index) => (
                  <div key={index} className={styles.notificationItem}>
                    <div className={styles.notificationIcon}>
                      {notification.event_type === 'user_follow' ? '👤' : 
                       notification.event_type === 'new_review' ? '📝' : '🔔'}
                    </div>
                    <div className={styles.notificationContent}>
                      <p className={styles.notificationMessage}>
                        {notification.data?.message || notification.event_type}
                      </p>
                      <span className={styles.notificationTime}>
                        {formatDate(notification.timestamp)}
                      </span>
                    </div>
                  </div>
                ))}
                {notifications.length > 10 && (
                  <p className={styles.moreText}>+ {notifications.length - 10} more</p>
                )}
              </div>
            )}
          </section>

          {/* Ratings History Section */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>📝 Your Reviews</h2>
            {reviews.length === 0 ? (
              <div className={styles.emptyState}>
                <p>You haven&apos;t written any reviews yet.</p>
                <button 
                  className={styles.ctaButton}
                  onClick={() => router.push("/movies")}
                >
                  Browse Movies
                </button>
              </div>
            ) : (
              <div className={styles.reviewsList}>
                {reviews.slice(0, 5).map((review) => (
                  <div 
                    key={review.review_id} 
                    className={styles.reviewCard}
                    onClick={() => router.push(`/movies/${review.movie_id}`)}
                  >
                    <div className={styles.reviewHeader}>
                      <span className={styles.movieTitle}>
                        {reviewMovies[review.movie_id]?.title || "Loading..."}
                      </span>
                      <span className={styles.reviewRating}>
                        {renderStars(review.rating)}
                      </span>
                    </div>
                    <p className={styles.reviewText}>{review.review_text}</p>
                    <span className={styles.reviewDate}>
                      {formatDate(review.review_date)}
                    </span>
                  </div>
                ))}
                {reviews.length > 5 && (
                  <p className={styles.moreText}>
                    + {reviews.length - 5} more reviews
                  </p>
                )}
              </div>
            )}
          </section>

          {/* Favorites Section */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>❤️ Favorites</h2>
            {favoriteMovies.length === 0 ? (
              <div className={styles.emptyState}>
                <p>You haven&apos;t added any favorites yet.</p>
                <button 
                  className={styles.ctaButton}
                  onClick={() => router.push("/movies")}
                >
                  Discover Movies
                </button>
              </div>
            ) : (
              <div className={styles.favoritesGrid}>
                {favoriteMovies.map((movie) => (
                  <div 
                    key={movie.movie_id} 
                    className={styles.favoriteCard}
                    onClick={() => router.push(`/movies/${movie.movie_id}`)}
                  >
                    <h4 className={styles.favoriteTitle}>{movie.title}</h4>
                    <p className={styles.favoriteMeta}>
                      {movie.year} • {movie.genre}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* All Penalties History */}
          {penalties.length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>📋 Penalty History</h2>
              <div className={styles.penaltiesList}>
                {penalties.map((penalty) => (
                  <div 
                    key={penalty.penalty_id} 
                    className={`${styles.penaltyCard} ${penalty.is_active ? styles.activePenalty : styles.expiredPenalty}`}
                  >
                    <div className={styles.penaltyCardHeader}>
                      <span className={styles.penaltyCardType}>{penalty.penalty_type}</span>
                      <span className={`${styles.penaltyStatus} ${penalty.is_active ? styles.active : styles.expired}`}>
                        {penalty.is_active ? "Active" : "Expired"}
                      </span>
                    </div>
                    <p className={styles.penaltyCardReason}>{penalty.reason}</p>
                    <div className={styles.penaltyCardMeta}>
                      <span>Issued: {formatDate(penalty.issued_at)}</span>
                      {penalty.expires_at && (
                        <span>Expires: {formatDate(penalty.expires_at)}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </main>

      {/* Blocked Users Modal */}
      {showBlockedModal && (
        <div className={styles.modalOverlay} onClick={() => setShowBlockedModal(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>🚫 Blocked Users</h2>
              <button 
                className={styles.modalClose}
                onClick={() => setShowBlockedModal(false)}
              >
                ✕
              </button>
            </div>
            <div className={styles.modalContent}>
              {blockedUsers.length === 0 ? (
                <p className={styles.emptyModal}>You haven&apos;t blocked anyone.</p>
              ) : (
                <div className={styles.blockedList}>
                  {blockedUsers.map((blockedUser) => (
                    <div key={blockedUser.userid} className={styles.blockedItem}>
                      <div className={styles.blockedInfo}>
                        <div className={styles.blockedAvatar}>
                          {blockedUser.username.charAt(0).toUpperCase()}
                        </div>
                        <span className={styles.blockedName}>{blockedUser.username}</span>
                      </div>
                      <button
                        className={styles.unblockButton}
                        onClick={() => handleUnblock(blockedUser.userid)}
                      >
                        Unblock
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
