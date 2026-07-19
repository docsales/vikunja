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

package models

import (
	"context"
	"testing"

	"code.vikunja.io/api/pkg/db"
	"code.vikunja.io/api/pkg/events"
	"code.vikunja.io/api/pkg/user"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestMigrateUserTasksAsAdmin(t *testing.T) {
	doer := &user.User{ID: 1}

	t.Run("moves created tasks and assignees, dropping collisions", func(t *testing.T) {
		adminActionsSetup(t)
		s := db.NewSession()
		defer s.Close()

		// Fixtures: 27 tasks have created_by_id 1. task_assignees has exactly
		// one row for user 1 (task 30), which user 2 is already assigned to -
		// that row must be dropped, not duplicated, so assigneesMoved is 0.
		tasksMoved, assigneesMoved, err := MigrateUserTasksAsAdmin(s, doer, 1, 2)
		require.NoError(t, err)
		require.NoError(t, s.Commit())
		events.DispatchPending(context.Background(), s)

		assert.EqualValues(t, 27, tasksMoved)
		assert.EqualValues(t, 0, assigneesMoved)

		evt := singleDispatchedEvent[*AdminUserTasksMigratedEvent](t)
		assert.Equal(t, int64(1), evt.From.ID)
		assert.Equal(t, int64(2), evt.To.ID)
		assert.EqualValues(t, 27, evt.TasksMoved)
		assert.EqualValues(t, 0, evt.AssigneesMoved)

		db.AssertExists(t, "tasks", map[string]interface{}{"id": 1, "created_by_id": 2}, false)
		db.AssertMissing(t, "task_assignees", map[string]interface{}{"task_id": 30, "user_id": 1})
		db.AssertExists(t, "task_assignees", map[string]interface{}{"task_id": 30, "user_id": 2}, false)
		db.AssertExists(t, "task_assignees", map[string]interface{}{"task_id": 35, "user_id": 2}, false)
	})

	t.Run("rejects migrating a user to themselves", func(t *testing.T) {
		adminActionsSetup(t)
		s := db.NewSession()
		defer s.Close()

		_, _, err := MigrateUserTasksAsAdmin(s, doer, 1, 1)
		require.Error(t, err)
		assert.True(t, IsErrInvalidData(err))
	})

	t.Run("errors for a nonexistent source user", func(t *testing.T) {
		adminActionsSetup(t)
		s := db.NewSession()
		defer s.Close()

		_, _, err := MigrateUserTasksAsAdmin(s, doer, 99999, 2)
		require.Error(t, err)
	})

	t.Run("errors for a nonexistent destination user", func(t *testing.T) {
		adminActionsSetup(t)
		s := db.NewSession()
		defer s.Close()

		_, _, err := MigrateUserTasksAsAdmin(s, doer, 1, 99999)
		require.Error(t, err)
	})
}
