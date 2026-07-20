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

package user

import (
	"testing"

	"github.com/asaskevich/govalidator"
	"github.com/stretchr/testify/assert"
)

func TestLanguageValidatorAllowsEmptyString(t *testing.T) {
	validate := govalidator.TagMap["language"]

	assert.True(t, validate(""), "an unspecified language should pass validation")
	assert.False(t, validate("not-a-real-language"), "an unregistered, non-empty language code should still fail validation")
}

func TestUsernameValidatorAllowsDottedNames(t *testing.T) {
	validate := govalidator.TagMap["username"]

	assert.True(t, validate("gustavo.arnaldo"), "a firstname.lastname username should pass validation")
	assert.True(t, validate("marcelo.medeiros"), "an existing dotted username convention should pass validation")
	assert.True(t, validate("mauriciokigiela"), "a plain username without dots should still pass validation")

	assert.False(t, validate("https://example.com"), "a string with a URL scheme should still fail validation")
	assert.False(t, validate("www.example.com"), "a www.-prefixed string should still fail validation")
	assert.False(t, validate("has space"), "a username with whitespace should still fail validation")
	assert.False(t, validate("has,comma"), "a username with a comma should still fail validation")
	assert.False(t, validate("link-share-42"), "the reserved link-share pattern should still fail validation")
}
