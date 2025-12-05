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

interface ReportedReview {
  report_id: string;
  review_id: string;
  reporting_user_id: string;
  reason: string;
  admin_viewed: boolean;
  timestamp: string;
  review_text: string;
  rating: number;
  movie_id: string;
  reviewer_user_id: string | null;
  imdb_username: string | null;
}

interface Movie {
  movie_id: string;
  title: string;
  year: number;
  genre: string;
}

export default function AdminReportsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [reports, setReports] = useState<ReportedReview[]>([]);
  const [movies, setMovies] = useState<Record<string, Movie>>({});
  const [reporterNames, setReporterNames] = useState<Record<string, string>>({});
  const [reviewerNames, setReviewerNames] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [filter, setFilter] = useState<"all" | "unviewed" | "viewed">("all");
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [confirmDeleteReview, setConfirmDeleteReview] = useState<string | null>(null);

  const REPORTS_PER_PAGE = 10;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const fetchReports = useCallback(async () => {
    try {
      const skip = (currentPage - 1) * REPORTS_PER_PAGE;
      let url = `${apiUrl}/reviews/reports/admin?skip=${skip}&limit=${REPORTS_PER_PAGE}`;
      
      if (filter === "unviewed") {
        url += "&admin_viewed=false";
      } else if (filter === "viewed") {
        url += "&admin_viewed=true";
      }

      const response = await fetch(url, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setReports(data.reports || []);
        setTotal(data.total || 0);

        // Fetch movie details for all reports
        const movieIds = [...new Set(data.reports.map((r: ReportedReview) => r.movie_id))];
        const movieMap: Record<string, Movie> = {};
        
        for (const movieId of movieIds) {
          try {
            const movieRes = await fetch(`${apiUrl}/movies/${movieId}`, {
              credentials: "include",
            });
            if (movieRes.ok) {
              const movieData = await movieRes.json();
              movieMap[movieId as string] = movieData;
            }
          } catch {
            // Ignore movie fetch errors
          }
        }
        setMovies(movieMap);

        // Fetch reporter usernames
        const reporterIds = [...new Set(data.reports.map((r: ReportedReview) => r.reporting_user_id))];
        const reviewerIds = [...new Set(data.reports.filter((r: ReportedReview) => r.reviewer_user_id).map((r: ReportedReview) => r.reviewer_user_id))];
        const allUserIds = [...new Set([...reporterIds, ...reviewerIds])];
        
        try {
          const searchRes = await fetch(`${apiUrl}/users/search/users?limit=100`, {
            credentials: "include",
          });
          if (searchRes.ok) {
            const searchData = await searchRes.json();
            const reporterMap: Record<string, string> = {};
            const reviewerMap: Record<string, string> = {};
            searchData.users?.forEach((u: { userid: string; username: string }) => {
              if (reporterIds.includes(u.userid)) {
                reporterMap[u.userid] = u.username;
              }
              if (reviewerIds.includes(u.userid)) {
                reviewerMap[u.userid] = u.username;
              }
            });
            setReporterNames(reporterMap);
            setReviewerNames(reviewerMap);
          }
        } catch {
          // Ignore user fetch errors
        }
      }
    } catch {
      // Ignore errors
    }
  }, [apiUrl, currentPage, filter]);

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
      fetchReports();
    }
  }, [user, fetchReports]);

  const handleMarkViewed = async (reportId: string) => {
    setActionLoading(reportId);
    try {
      const response = await fetch(`${apiUrl}/reviews/reports/${reportId}/admin/view`, {
        method: "PATCH",
        credentials: "include",
      });

      if (response.ok) {
        // Update local state
        setReports(prev => prev.map(r => 
          r.report_id === reportId ? { ...r, admin_viewed: true } : r
        ));
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null);
    }
  };

  const handleDismissReport = async (reportId: string) => {
    setActionLoading(reportId);
    try {
      const response = await fetch(`${apiUrl}/reviews/reports/${reportId}/admin`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.ok) {
        // Remove from local state
        setReports(prev => prev.filter(r => r.report_id !== reportId));
        setTotal(prev => prev - 1);
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null);
      setConfirmDelete(null);
    }
  };

  const handleDeleteReview = async (reviewId: string, reportId: string) => {
    setActionLoading(reportId);
    try {
      const response = await fetch(`${apiUrl}/reviews/${reviewId}/admin`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.ok) {
        // Remove from local state (review deleted means report is orphaned)
        setReports(prev => prev.filter(r => r.review_id !== reviewId));
        setTotal(prev => prev - 1);
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(null);
      setConfirmDeleteReview(null);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const renderStars = (rating: number) => {
    return "⭐".repeat(rating) + "☆".repeat(5 - rating);
  };

  const totalPages = Math.ceil(total / REPORTS_PER_PAGE);

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
            <h1 className={styles.title}>⚠️ Reported Reviews</h1>
            <p className={styles.subtitle}>Review and moderate reported content</p>
          </div>

          {/* Filter Tabs */}
          <div className={styles.filterTabs}>
            <button
              className={`${styles.filterTab} ${filter === "all" ? styles.active : ""}`}
              onClick={() => { setFilter("all"); setCurrentPage(1); }}
            >
              All ({total})
            </button>
            <button
              className={`${styles.filterTab} ${filter === "unviewed" ? styles.active : ""}`}
              onClick={() => { setFilter("unviewed"); setCurrentPage(1); }}
            >
              🔴 Unviewed
            </button>
            <button
              className={`${styles.filterTab} ${filter === "viewed" ? styles.active : ""}`}
              onClick={() => { setFilter("viewed"); setCurrentPage(1); }}
            >
              ✓ Viewed
            </button>
          </div>

          {/* Reports List */}
          {reports.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No reported reviews {filter !== "all" ? `(${filter})` : ""}</p>
            </div>
          ) : (
            <div className={styles.reportsList}>
              {reports.map((report) => (
                <div 
                  key={report.report_id} 
                  className={`${styles.reportCard} ${!report.admin_viewed ? styles.unviewed : ""}`}
                >
                  <div className={styles.reportHeader}>
                    <div className={styles.reportMeta}>
                      {!report.admin_viewed && <span className={styles.newBadge}>NEW</span>}
                      <span className={styles.reportDate}>
                        Reported: {formatDate(report.timestamp)}
                      </span>
                    </div>
                    <div className={styles.reportActions}>
                      {!report.admin_viewed && (
                        <button
                          className={styles.markViewedButton}
                          onClick={() => handleMarkViewed(report.report_id)}
                          disabled={actionLoading === report.report_id}
                        >
                          {actionLoading === report.report_id ? "..." : "Mark as Viewed"}
                        </button>
                      )}
                    </div>
                  </div>

                  <div className={styles.reportContent}>
                    {/* Reporter Info */}
                    <div className={styles.reporterInfo}>
                      <span className={styles.label}>Reported by:</span>
                      <span className={styles.value}>
                        {reporterNames[report.reporting_user_id] || report.reporting_user_id}
                      </span>
                    </div>

                    {/* Report Reason */}
                    {report.reason && (
                      <div className={styles.reportReason}>
                        <span className={styles.label}>Reason:</span>
                        <p className={styles.reasonText}>{report.reason}</p>
                      </div>
                    )}

                    {/* Review Content */}
                    <div className={styles.reviewContent}>
                      <div className={styles.reviewContentHeader}>
                        <h4>Reported Review</h4>
                        <span 
                          className={styles.movieLink}
                          onClick={() => router.push(`/movies/${report.movie_id}`)}
                        >
                          {movies[report.movie_id]?.title || "Loading..."} ({movies[report.movie_id]?.year || "..."})
                        </span>
                      </div>
                      <div className={styles.reviewerInfo}>
                        <span className={styles.reviewerName}>
                          {report.reviewer_user_id 
                            ? reviewerNames[report.reviewer_user_id] || report.reviewer_user_id
                            : report.imdb_username || "Anonymous"}
                        </span>
                        <span className={styles.reviewRating}>{renderStars(report.rating)}</span>
                      </div>
                      <p className={styles.reviewText}>{report.review_text}</p>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className={styles.actionButtons}>
                    {confirmDelete === report.report_id ? (
                      <div className={styles.confirmGroup}>
                        <span>Dismiss this report?</span>
                        <button
                          className={styles.confirmYes}
                          onClick={() => handleDismissReport(report.report_id)}
                          disabled={actionLoading === report.report_id}
                        >
                          Yes, Dismiss
                        </button>
                        <button
                          className={styles.confirmNo}
                          onClick={() => setConfirmDelete(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : confirmDeleteReview === report.report_id ? (
                      <div className={styles.confirmGroup}>
                        <span>Delete this review permanently?</span>
                        <button
                          className={styles.deleteConfirmYes}
                          onClick={() => handleDeleteReview(report.review_id, report.report_id)}
                          disabled={actionLoading === report.report_id}
                        >
                          Yes, Delete Review
                        </button>
                        <button
                          className={styles.confirmNo}
                          onClick={() => setConfirmDeleteReview(null)}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <>
                        <button
                          className={styles.dismissButton}
                          onClick={() => setConfirmDelete(report.report_id)}
                          disabled={actionLoading === report.report_id}
                        >
                          ✓ Dismiss Report
                        </button>
                        <button
                          className={styles.deleteReviewButton}
                          onClick={() => setConfirmDeleteReview(report.report_id)}
                          disabled={actionLoading === report.report_id}
                        >
                          🗑️ Delete Review
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className={styles.pageButton}
                onClick={() => setCurrentPage(prev => prev - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </button>
              <span className={styles.pageInfo}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                className={styles.pageButton}
                onClick={() => setCurrentPage(prev => prev + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
