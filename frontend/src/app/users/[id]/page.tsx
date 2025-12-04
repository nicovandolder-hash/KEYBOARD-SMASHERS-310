"use client";

import { useEffect, useState, use } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import styles from "./page.module.css";

interface CurrentUser {
  userid: string;
  username: string;
  is_admin: boolean;
}

interface UserProfile {
  userid: string;
  username: string;
  total_reviews: number;
  favorites: string[];
  creation_date: string;
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

interface FollowData {
  total: number;
  followers?: Array<{ userid: string; username: string }>;
  following?: Array<{ userid: string; username: string }>;
}

export default function UserProfilePage({ params }: { params: Promise<{ id: string }> }) {
  const { id: userId } = use(params);
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [favoriteMovies, setFavoriteMovies] = useState<Movie[]>([]);
  const [reviewMovies, setReviewMovies] = useState<Record<string, Movie>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isFollowing, setIsFollowing] = useState(false);
  const [isBlocked, setIsBlocked] = useState(false);
  const [followerCount, setFollowerCount] = useState(0);
  const [followingCount, setFollowingCount] = useState(0);
  const [actionLoading, setActionLoading] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch current user
        const currentUserRes = await fetch(`${apiUrl}/users/me`, {
          credentials: "include",
        });
        
        if (currentUserRes.ok) {
          const currentUserData = await currentUserRes.json();
          setCurrentUser(currentUserData);

          // Check if viewing own profile
          if (currentUserData.userid === userId) {
            router.push("/dashboard");
            return;
          }

          // Check if user is following this profile
          const followingRes = await fetch(`${apiUrl}/users/${currentUserData.userid}/following?limit=1000`, {
            credentials: "include",
          });
          if (followingRes.ok) {
            const followingData = await followingRes.json();
            const isFollowingUser = followingData.following?.some(
              (f: { userid: string }) => f.userid === userId
            );
            setIsFollowing(isFollowingUser);
          }

          // Check if user has blocked this profile
          const blockedRes = await fetch(`${apiUrl}/users/me/blocked`, {
            credentials: "include",
          });
          if (blockedRes.ok) {
            const blockedData = await blockedRes.json();
            const hasBlocked = blockedData.blocked_users?.some(
              (b: { userid: string }) => b.userid === userId
            );
            setIsBlocked(hasBlocked);
          }
        }

        // Fetch profile user data using search endpoint
        const searchRes = await fetch(`${apiUrl}/users/search/users?q=`, {
          credentials: "include",
        });
        
        if (!searchRes.ok) {
          router.push("/dashboard");
          return;
        }
        
        const searchData = await searchRes.json();
        const profileData = searchData.users?.find((u: UserProfile) => u.userid === userId);
        
        if (!profileData) {
          router.push("/dashboard");
          return;
        }
        
        setProfile(profileData);

        // Fetch followers/following counts
        const [followersRes, followingRes] = await Promise.all([
          fetch(`${apiUrl}/users/${userId}/followers?limit=1`, { credentials: "include" }),
          fetch(`${apiUrl}/users/${userId}/following?limit=1`, { credentials: "include" }),
        ]);

        if (followersRes.ok) {
          const data: FollowData = await followersRes.json();
          setFollowerCount(data.total);
        }
        if (followingRes.ok) {
          const data: FollowData = await followingRes.json();
          setFollowingCount(data.total);
        }

        // Fetch user's reviews
        const reviewsRes = await fetch(`${apiUrl}/reviews/user/${userId}?limit=50`, {
          credentials: "include",
        });
        if (reviewsRes.ok) {
          const reviewsData = await reviewsRes.json();
          setReviews(reviewsData.reviews || []);

          // Fetch movie details for reviews
          const movieIds = [...new Set(reviewsData.reviews?.map((r: Review) => r.movie_id) || [])];
          const movieDetails: Record<string, Movie> = {};
          await Promise.all(
            movieIds.map(async (movieId) => {
              try {
                const movieRes = await fetch(`${apiUrl}/movies/${movieId}`, {
                  credentials: "include",
                });
                if (movieRes.ok) {
                  movieDetails[movieId as string] = await movieRes.json();
                }
              } catch {
                // Skip
              }
            })
          );
          setReviewMovies(movieDetails);
        }

        // Fetch favorite movies
        if (profileData.favorites && profileData.favorites.length > 0) {
          const favMovies: Movie[] = [];
          await Promise.all(
            profileData.favorites.map(async (movieId: string) => {
              try {
                const movieRes = await fetch(`${apiUrl}/movies/${movieId}`, {
                  credentials: "include",
                });
                if (movieRes.ok) {
                  favMovies.push(await movieRes.json());
                }
              } catch {
                // Skip
              }
            })
          );
          setFavoriteMovies(favMovies);
        }

      } catch {
        router.push("/dashboard");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [userId, router, apiUrl]);

  const handleFollow = async () => {
    if (!currentUser || actionLoading) return;
    setActionLoading(true);

    try {
      const method = isFollowing ? "DELETE" : "POST";
      const response = await fetch(`${apiUrl}/users/${userId}/follow`, {
        method,
        credentials: "include",
      });

      if (response.ok) {
        setIsFollowing(!isFollowing);
        setFollowerCount((prev) => (isFollowing ? prev - 1 : prev + 1));
      }
    } catch {
      // Ignore
    } finally {
      setActionLoading(false);
    }
  };

  const handleBlock = async () => {
    if (!currentUser || actionLoading) return;
    setActionLoading(true);

    try {
      const method = isBlocked ? "DELETE" : "POST";
      const response = await fetch(`${apiUrl}/users/${userId}/block`, {
        method,
        credentials: "include",
      });

      if (response.ok) {
        setIsBlocked(!isBlocked);
        // If blocking, also unfollow
        if (!isBlocked && isFollowing) {
          setIsFollowing(false);
          setFollowerCount((prev) => prev - 1);
        }
      }
    } catch {
      // Ignore
    } finally {
      setActionLoading(false);
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

  if (!profile) {
    return null;
  }

  return (
    <div className={styles.pageWrapper}>
      <Navbar username={currentUser?.username} isAdmin={currentUser?.is_admin} />
      <main className={styles.main}>
        <div className={styles.container}>
          <button className={styles.backButton} onClick={() => router.back()}>
            ← Back
          </button>

          {/* Profile Header */}
          <div className={styles.profileHeader}>
            <div className={styles.avatarLarge}>
              {profile.username.charAt(0).toUpperCase()}
            </div>
            <div className={styles.profileInfo}>
              <h1 className={styles.profileName}>{profile.username}</h1>
              <p className={styles.profileMeta}>
                Member since {profile.creation_date ? formatDate(profile.creation_date) : "N/A"}
              </p>
            </div>
            {currentUser && (
              <div className={styles.profileActions}>
                <button
                  className={`${styles.actionButton} ${isFollowing ? styles.following : styles.follow}`}
                  onClick={handleFollow}
                  disabled={actionLoading || isBlocked}
                >
                  {isFollowing ? "Unfollow" : "Follow"}
                </button>
                <button
                  className={`${styles.actionButton} ${styles.block} ${isBlocked ? styles.blocked : ""}`}
                  onClick={handleBlock}
                  disabled={actionLoading}
                >
                  {isBlocked ? "Unblock" : "Block"}
                </button>
              </div>
            )}
          </div>

          {/* Stats */}
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
          </div>

          {/* Reviews Section */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>📝 Reviews</h2>
            {reviews.length === 0 ? (
              <div className={styles.emptyState}>
                <p>This user hasn&apos;t written any reviews yet.</p>
              </div>
            ) : (
              <div className={styles.reviewsList}>
                {reviews.slice(0, 10).map((review) => (
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
                {reviews.length > 10 && (
                  <p className={styles.moreText}>+ {reviews.length - 10} more reviews</p>
                )}
              </div>
            )}
          </section>

          {/* Favorites Section */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>❤️ Favorites</h2>
            {favoriteMovies.length === 0 ? (
              <div className={styles.emptyState}>
                <p>This user hasn&apos;t added any favorites yet.</p>
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
        </div>
      </main>
    </div>
  );
}
