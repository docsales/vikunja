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

// This file holds admin actions specific to this fork (docsales/vikunja),
// kept out of the upstream-mirrored admin_user_*.go files to avoid conflicts
// on future upstream syncs.
package models

import (
	"code.vikunja.io/api/pkg/events"
	"code.vikunja.io/api/pkg/user"

	"xorm.io/xorm"
)

// MigrateUserTasksAsAdmin reassigns every task created by or assigned to
// fromID over to toID - for merging a duplicate account (e.g. a new OIDC
// login) into the account that already holds the task history. Assignments
// fromID already shares with toID are dropped rather than duplicated. It
// does not commit; the caller owns the transaction.
func MigrateUserTasksAsAdmin(s *xorm.Session, doer *user.User, fromID, toID int64) (tasksMoved, assigneesMoved int64, err error) {
	from, err := loadAdminTargetUser(s, fromID)
	if err != nil {
		return 0, 0, err
	}
	to, err := loadAdminTargetUser(s, toID)
	if err != nil {
		return 0, 0, err
	}
	if from.ID == to.ID {
		return 0, 0, ErrInvalidData{Message: "source and destination user must be different"}
	}

	tasksMoved, err = s.Table("tasks").
		Where("created_by_id = ?", from.ID).
		Update(map[string]interface{}{"created_by_id": to.ID})
	if err != nil {
		return 0, 0, err
	}

	// task_assignees has a unique (task_id, user_id) pair, so tasks `to` is
	// already assigned to can't be reassigned from `from` without violating
	// it - drop `from`'s row on those instead of moving it.
	var alreadyAssignedTaskIDs []int64
	if err := s.Table("task_assignees").Where("user_id = ?", to.ID).Cols("task_id").Find(&alreadyAssignedTaskIDs); err != nil {
		return 0, 0, err
	}

	moveQuery := s.Table("task_assignees").Where("user_id = ?", from.ID)
	if len(alreadyAssignedTaskIDs) > 0 {
		moveQuery = moveQuery.NotIn("task_id", alreadyAssignedTaskIDs)
	}
	assigneesMoved, err = moveQuery.Update(map[string]interface{}{"user_id": to.ID})
	if err != nil {
		return 0, 0, err
	}

	if len(alreadyAssignedTaskIDs) > 0 {
		if _, err := s.Table("task_assignees").
			Where("user_id = ?", from.ID).
			In("task_id", alreadyAssignedTaskIDs).
			Delete(&TaskAssginee{}); err != nil {
			return 0, 0, err
		}
	}

	events.DispatchOnCommit(s, &AdminUserTasksMigratedEvent{
		From:           from,
		To:             to,
		Doer:           doer,
		TasksMoved:     tasksMoved,
		AssigneesMoved: assigneesMoved,
	})

	return tasksMoved, assigneesMoved, nil
}
