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
  email?: string;
  is_admin: boolean;
  is_suspended: boolean;
  total_reviews: number;
  total_penalty_count: number;
  reputation: number;
}

interface Penalty {
  penalty_id: string;
  user_id: string;
  admin_id: string;
  reason: string;
  severity: number;
  start_date: string;
  end_date: string | null;
  created_at: string;
  is_active: boolean;
}

interface PenaltySummary {
  user_id: string;
  active_penalties: Penalty[];
  historical_penalties: Penalty[];
  total_active: number;
  total_historical: number;
}

export default function AdminUsersPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [users, setUsers] = useState<PublicUser[]>([]);
  const [selectedUser, setSelectedUser] = useState<PublicUser | null>(null);
  const [penaltySummary, setPenaltySummary] = useState<PenaltySummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [usersLoading, setUsersLoading] = useState(false);
  const [penaltiesLoading, setPenaltiesLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // User search/pagination
  const [userSearchQuery, setUserSearchQuery] = useState("");
  const [userPage, setUserPage] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const USERS_PER_PAGE = 15;

  // Penalty form
  const [showPenaltyForm, setShowPenaltyForm] = useState(false);
  const [penaltyReason, setPenaltyReason] = useState("");
  const [penaltySeverity, setPenaltySeverity] = useState(1);
  const [penaltyEndDate, setPenaltyEndDate] = useState("");

  // Confirmation dialogs
  const [confirmAction, setConfirmAction] = useState<"suspend" | "reactivate" | "delete" | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Store all users fetched from admin endpoint
  const [allUsers, setAllUsers] = useState<PublicUser[]>([]);

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      // Use admin endpoint to get full user data including is_suspended
      const response = await fetch(`${apiUrl}/users/`, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setAllUsers(data || []);
      }
    } catch {
      // Ignore errors
    } finally {
      setUsersLoading(false);
    }
  }, [apiUrl]);

  // Client-side filtering and pagination
  useEffect(() => {
    let filtered = allUsers;
    
    // Filter by search query
    if (userSearchQuery) {
      const query = userSearchQuery.toLowerCase();
      filtered = filtered.filter(u => u.username.toLowerCase().includes(query));
    }
    
    // Sort alphabetically
    filtered.sort((a, b) => a.username.toLowerCase().localeCompare(b.username.toLowerCase()));
    
    setTotalUsers(filtered.length);
    
    // Paginate
    const offset = (userPage - 1) * USERS_PER_PAGE;
    setUsers(filtered.slice(offset, offset + USERS_PER_PAGE));
  }, [allUsers, userSearchQuery, userPage]);

  const fetchPenaltySummary = useCallback(async (userId: string) => {
    setPenaltiesLoading(true);
    try {
      const response = await fetch(`${apiUrl}/penalties/user/${userId}/summary`, {
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        setPenaltySummary(data);
      } else {
        setPenaltySummary(null);
      }
    } catch {
      setPenaltySummary(null);
    } finally {
      setPenaltiesLoading(false);
    }
  }, [apiUrl]);

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
  }, [user]);

  useEffect(() => {
    if (selectedUser) {
      fetchPenaltySummary(selectedUser.userid);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedUser]);

  const handleUserSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setUserPage(1);
    setSelectedUser(null);
    setPenaltySummary(null);
    // No need to fetch - filtering is done client-side
  };

  const handleSelectUser = (u: PublicUser) => {
    setSelectedUser(u);
    setShowPenaltyForm(false);
    setConfirmAction(null);
  };

  const handleSuspendUser = async () => {
    if (!selectedUser) return;
    setActionLoading(true);
    try {
      const response = await fetch(`${apiUrl}/users/${selectedUser.userid}/suspend`, {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        // Update local state - update allUsers so filtering works correctly
        setAllUsers(prev => prev.map(u =>
          u.userid === selectedUser.userid ? { ...u, is_suspended: true } : u
        ));
        setSelectedUser(prev => prev ? { ...prev, is_suspended: true } : null);
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  };

  const handleReactivateUser = async () => {
    if (!selectedUser) return;
    setActionLoading(true);
    try {
      const response = await fetch(`${apiUrl}/users/${selectedUser.userid}/reactivate`, {
        method: "POST",
        credentials: "include",
      });

      if (response.ok) {
        // Update local state - update allUsers so filtering works correctly
        setAllUsers(prev => prev.map(u =>
          u.userid === selectedUser.userid ? { ...u, is_suspended: false } : u
        ));
        setSelectedUser(prev => prev ? { ...prev, is_suspended: false } : null);
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    setActionLoading(true);
    try {
      const response = await fetch(`${apiUrl}/users/${selectedUser.userid}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.ok) {
        // Remove from allUsers and clear selection
        setAllUsers(prev => prev.filter(u => u.userid !== selectedUser.userid));
        setSelectedUser(null);
        setPenaltySummary(null);
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(false);
      setConfirmAction(null);
    }
  };

  const handleCreatePenalty = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser || !penaltyReason.trim()) return;
    
    setActionLoading(true);
    try {
      const payload: {
        user_id: string;
        reason: string;
        severity: number;
        end_date?: string;
      } = {
        user_id: selectedUser.userid,
        reason: penaltyReason.trim(),
        severity: penaltySeverity,
      };

      if (penaltyEndDate) {
        payload.end_date = new Date(penaltyEndDate).toISOString();
      }

      const response = await fetch(`${apiUrl}/penalties/`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        // Refresh penalty summary
        fetchPenaltySummary(selectedUser.userid);
        // Reset form
        setPenaltyReason("");
        setPenaltySeverity(1);
        setPenaltyEndDate("");
        setShowPenaltyForm(false);
        // Update penalty count in allUsers
        setAllUsers(prev => prev.map(u =>
          u.userid === selectedUser.userid 
            ? { ...u, total_penalty_count: (u.total_penalty_count || 0) + 1 } 
            : u
        ));
        setSelectedUser(prev => prev 
          ? { ...prev, total_penalty_count: (prev.total_penalty_count || 0) + 1 } 
          : null
        );
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeletePenalty = async (penaltyId: string) => {
    if (!selectedUser) return;
    setActionLoading(true);
    try {
      const response = await fetch(`${apiUrl}/penalties/${penaltyId}`, {
        method: "DELETE",
        credentials: "include",
      });

      if (response.ok) {
        // Refresh penalty summary
        fetchPenaltySummary(selectedUser.userid);
        // Update penalty count in allUsers
        setAllUsers(prev => prev.map(u =>
          u.userid === selectedUser.userid
            ? { ...u, total_penalty_count: Math.max(0, (u.total_penalty_count || 0) - 1) }
            : u
        ));
        setSelectedUser(prev => prev
          ? { ...prev, total_penalty_count: Math.max(0, (prev.total_penalty_count || 0) - 1) }
          : null
        );
      }
    } catch {
      // Ignore errors
    } finally {
      setActionLoading(false);
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

  const getSeverityLabel = (severity: number) => {
    const labels = ["", "Minor", "Low", "Medium", "High", "Severe"];
    return labels[severity] || "Unknown";
  };

  const getSeverityColor = (severity: number) => {
    const colors = ["", "#4ade80", "#facc15", "#fb923c", "#f87171", "#dc2626"];
    return colors[severity] || "#888";
  };

  const totalUserPages = Math.ceil(totalUsers / USERS_PER_PAGE);

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
            <h1 className={styles.title}>👥 User Management</h1>
            <p className={styles.subtitle}>Manage users, suspensions, and penalties</p>
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
                <div className={styles.emptyState}>No users found</div>
              ) : (
                <>
                  <div className={styles.usersList}>
                    {users.map((u) => (
                      <div
                        key={u.userid}
                        className={`${styles.userCard} ${selectedUser?.userid === u.userid ? styles.selected : ""} ${u.is_suspended ? styles.suspended : ""}`}
                        onClick={() => handleSelectUser(u)}
                      >
                        <div className={styles.userAvatar}>
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <div className={styles.userInfo}>
                          <span className={styles.userName}>
                            {u.username}
                            {u.is_admin && <span className={styles.adminBadge}>Admin</span>}
                            {u.is_suspended && <span className={styles.suspendedBadge}>Suspended</span>}
                          </span>
                          <span className={styles.userMeta}>
                            {u.total_penalty_count > 0 && (
                              <span className={styles.penaltyCount}>⚠️ {u.total_penalty_count} penalties</span>
                            )}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalUserPages > 1 && (
                    <div className={styles.pagination}>
                      <button
                        onClick={() => setUserPage(p => Math.max(1, p - 1))}
                        disabled={userPage === 1}
                        className={styles.pageButton}
                      >
                        ←
                      </button>
                      <span className={styles.pageInfo}>
                        {userPage} / {totalUserPages}
                      </span>
                      <button
                        onClick={() => setUserPage(p => Math.min(totalUserPages, p + 1))}
                        disabled={userPage === totalUserPages}
                        className={styles.pageButton}
                      >
                        →
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* User Details Panel */}
            <div className={styles.detailsPanel}>
              {!selectedUser ? (
                <div className={styles.emptyStatePanel}>
                  <span className={styles.emptyIcon}>👆</span>
                  <p>Select a user to manage</p>
                </div>
              ) : (
                <>
                  {/* User Header */}
                  <div className={styles.userHeader}>
                    <div className={styles.userHeaderAvatar}>
                      {selectedUser.username.charAt(0).toUpperCase()}
                    </div>
                    <div className={styles.userHeaderInfo}>
                      <h2 className={styles.userHeaderName}>
                        {selectedUser.username}
                        {selectedUser.is_admin && <span className={styles.adminBadgeLarge}>Admin</span>}
                      </h2>
                      <p className={styles.userHeaderMeta}>
                        User ID: {selectedUser.userid}
                      </p>
                      <div className={styles.statusBadges}>
                        {selectedUser.is_suspended ? (
                          <span className={styles.statusSuspended}>🚫 Suspended</span>
                        ) : (
                          <span className={styles.statusActive}>✓ Active</span>
                        )}
                        <span className={styles.reputation}>⭐ Rep: {selectedUser.reputation}</span>
                      </div>
                    </div>
                  </div>

                  {/* Action Buttons */}
                  {!selectedUser.is_admin && (
                    <div className={styles.actionButtons}>
                      {selectedUser.is_suspended ? (
                        <button
                          onClick={() => setConfirmAction("reactivate")}
                          className={styles.reactivateButton}
                          disabled={actionLoading}
                        >
                          ✓ Reactivate User
                        </button>
                      ) : (
                        <button
                          onClick={() => setConfirmAction("suspend")}
                          className={styles.suspendButton}
                          disabled={actionLoading}
                        >
                          🚫 Suspend User
                        </button>
                      )}
                      <button
                        onClick={() => setConfirmAction("delete")}
                        className={styles.deleteButton}
                        disabled={actionLoading}
                      >
                        🗑️ Delete User
                      </button>
                      <button
                        onClick={() => setShowPenaltyForm(!showPenaltyForm)}
                        className={styles.penaltyButton}
                        disabled={actionLoading}
                      >
                        ⚠️ Add Penalty
                      </button>
                    </div>
                  )}

                  {/* Confirmation Dialog */}
                  {confirmAction && (
                    <div className={styles.confirmDialog}>
                      <p className={styles.confirmText}>
                        {confirmAction === "suspend" && `Are you sure you want to suspend ${selectedUser.username}?`}
                        {confirmAction === "reactivate" && `Are you sure you want to reactivate ${selectedUser.username}?`}
                        {confirmAction === "delete" && `Are you sure you want to permanently delete ${selectedUser.username}? This cannot be undone.`}
                      </p>
                      <div className={styles.confirmButtons}>
                        <button
                          onClick={() => {
                            if (confirmAction === "suspend") handleSuspendUser();
                            else if (confirmAction === "reactivate") handleReactivateUser();
                            else if (confirmAction === "delete") handleDeleteUser();
                          }}
                          className={styles.confirmYes}
                          disabled={actionLoading}
                        >
                          {actionLoading ? "Processing..." : "Yes, confirm"}
                        </button>
                        <button
                          onClick={() => setConfirmAction(null)}
                          className={styles.confirmNo}
                          disabled={actionLoading}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Penalty Form */}
                  {showPenaltyForm && (
                    <form onSubmit={handleCreatePenalty} className={styles.penaltyForm}>
                      <h3 className={styles.formTitle}>Add New Penalty</h3>
                      
                      <div className={styles.formGroup}>
                        <label className={styles.formLabel}>Reason *</label>
                        <textarea
                          value={penaltyReason}
                          onChange={(e) => setPenaltyReason(e.target.value)}
                          placeholder="Enter reason for penalty..."
                          className={styles.formTextarea}
                          required
                          minLength={5}
                        />
                      </div>

                      <div className={styles.formRow}>
                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>Severity (1-5)</label>
                          <select
                            value={penaltySeverity}
                            onChange={(e) => setPenaltySeverity(Number(e.target.value))}
                            className={styles.formSelect}
                          >
                            <option value={1}>1 - Minor</option>
                            <option value={2}>2 - Low</option>
                            <option value={3}>3 - Medium</option>
                            <option value={4}>4 - High</option>
                            <option value={5}>5 - Severe</option>
                          </select>
                        </div>

                        <div className={styles.formGroup}>
                          <label className={styles.formLabel}>End Date (optional)</label>
                          <input
                            type="date"
                            value={penaltyEndDate}
                            onChange={(e) => setPenaltyEndDate(e.target.value)}
                            className={styles.formInput}
                            min={new Date().toISOString().split("T")[0]}
                          />
                        </div>
                      </div>

                      <div className={styles.formButtons}>
                        <button
                          type="submit"
                          className={styles.submitButton}
                          disabled={actionLoading || !penaltyReason.trim()}
                        >
                          {actionLoading ? "Submitting..." : "Submit Penalty"}
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowPenaltyForm(false)}
                          className={styles.cancelButton}
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}

                  {/* Penalties Section */}
                  <div className={styles.penaltiesSection}>
                    <h3 className={styles.sectionTitle}>Penalty History</h3>
                    
                    {penaltiesLoading ? (
                      <div className={styles.loadingSmall}>Loading penalties...</div>
                    ) : !penaltySummary ? (
                      <div className={styles.emptyPenalties}>No penalty data available</div>
                    ) : (
                      <>
                        {/* Active Penalties */}
                        {penaltySummary.active_penalties.length > 0 && (
                          <div className={styles.penaltyGroup}>
                            <h4 className={styles.penaltyGroupTitle}>
                              🔴 Active Penalties ({penaltySummary.total_active})
                            </h4>
                            {penaltySummary.active_penalties.map((penalty) => (
                              <div key={penalty.penalty_id} className={styles.penaltyCard}>
                                <div className={styles.penaltyHeader}>
                                  <span 
                                    className={styles.severityBadge}
                                    style={{ backgroundColor: getSeverityColor(penalty.severity) }}
                                  >
                                    {getSeverityLabel(penalty.severity)}
                                  </span>
                                  <span className={styles.penaltyDate}>
                                    {formatDate(penalty.start_date)}
                                    {penalty.end_date && ` - ${formatDate(penalty.end_date)}`}
                                    {!penalty.end_date && " - Permanent"}
                                  </span>
                                </div>
                                <p className={styles.penaltyReason}>{penalty.reason}</p>
                                <button
                                  onClick={() => handleDeletePenalty(penalty.penalty_id)}
                                  className={styles.deletePenaltyButton}
                                  disabled={actionLoading}
                                >
                                  🗑️ Remove
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {/* Historical Penalties */}
                        {penaltySummary.historical_penalties.length > 0 && (
                          <div className={styles.penaltyGroup}>
                            <h4 className={styles.penaltyGroupTitle}>
                              📋 Historical Penalties ({penaltySummary.total_historical})
                            </h4>
                            {penaltySummary.historical_penalties.map((penalty) => (
                              <div key={penalty.penalty_id} className={`${styles.penaltyCard} ${styles.historical}`}>
                                <div className={styles.penaltyHeader}>
                                  <span 
                                    className={styles.severityBadge}
                                    style={{ backgroundColor: getSeverityColor(penalty.severity), opacity: 0.7 }}
                                  >
                                    {getSeverityLabel(penalty.severity)}
                                  </span>
                                  <span className={styles.penaltyDate}>
                                    {formatDate(penalty.start_date)}
                                    {penalty.end_date && ` - ${formatDate(penalty.end_date)}`}
                                  </span>
                                </div>
                                <p className={styles.penaltyReason}>{penalty.reason}</p>
                                <button
                                  onClick={() => handleDeletePenalty(penalty.penalty_id)}
                                  className={styles.deletePenaltyButton}
                                  disabled={actionLoading}
                                >
                                  🗑️ Remove
                                </button>
                              </div>
                            ))}
                          </div>
                        )}

                        {penaltySummary.total_active === 0 && penaltySummary.total_historical === 0 && (
                          <div className={styles.emptyPenalties}>No penalties on record</div>
                        )}
                      </>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
