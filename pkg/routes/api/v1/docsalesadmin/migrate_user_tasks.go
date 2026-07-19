// Vikunja is a to-do list application to facilitate your life.
// Copyright 2018-present Vikunja and contributors. All rights reserved.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

// Package docsalesadmin holds admin-only HTTP handlers specific to this fork
// (docsales/vikunja), registered outside Vikunja's own license-gated /admin
// group - see pkg/license/license.go before extending what's exposed here.
package docsalesadmin

import (
	"net/http"
	"strconv"

	"code.vikunja.io/api/pkg/db"
	"code.vikunja.io/api/pkg/events"
	"code.vikunja.io/api/pkg/models"
	"code.vikunja.io/api/pkg/user"

	"github.com/labstack/echo/v5"
)

// migrateUserTasksResult is the response body for MigrateUserTasks.
type migrateUserTasksResult struct {
	TasksMoved     int64 `json:"tasks_moved"`
	AssigneesMoved int64 `json:"assignees_moved"`
}

// MigrateUserTasks reassigns every task created by or assigned to the :from
// user over to the :to user.
// @Summary Migrate a user's tasks to another user (admin)
// @Description Reassigns every task created by or assigned to the :from user over to the :to user - for merging a duplicate account (e.g. a new OIDC login) into the account that already holds the task history. The :from user account itself is untouched; deactivate or delete it separately if desired.
// @tags docsales-admin
// @Produce json
// @Security JWTKeyAuth
// @Param from path int true "Source user ID"
// @Param to path int true "Destination user ID"
// @Success 200 {object} migrateUserTasksResult
// @Failure 400 {object} web.HTTPError
// @Failure 404 {object} web.HTTPError
// @Router /docsales-admin/users/{from}/migrate-to/{to} [post]
func MigrateUserTasks(c *echo.Context) error {
	fromID, err := strconv.ParseInt(c.Param("from"), 10, 64)
	if err != nil || fromID < 1 {
		return user.ErrUserDoesNotExist{UserID: fromID}
	}
	toID, err := strconv.ParseInt(c.Param("to"), 10, 64)
	if err != nil || toID < 1 {
		return user.ErrUserDoesNotExist{UserID: toID}
	}

	doer, err := user.GetCurrentUser(c)
	if err != nil {
		return err
	}

	s := db.NewSession()
	defer s.Close()

	tasksMoved, assigneesMoved, err := models.MigrateUserTasksAsAdmin(s, doer, fromID, toID)
	if err != nil {
		_ = s.Rollback()
		events.CleanupPending(s)
		return err
	}
	if err := s.Commit(); err != nil {
		events.CleanupPending(s)
		return err
	}
	events.DispatchPending(c.Request().Context(), s)

	return c.JSON(http.StatusOK, &migrateUserTasksResult{
		TasksMoved:     tasksMoved,
		AssigneesMoved: assigneesMoved,
	})
}
