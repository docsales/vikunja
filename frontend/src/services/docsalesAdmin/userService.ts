import AbstractService from '@/services/abstractService'
import AdminUserModel from '@/models/adminUser'
import type {IAdminUser} from '@/modelTypes/IAdminUser'

export interface CreateDocsalesAdminUserBody {
	username: string
	email: string
	password: string
	name?: string
	language?: string
	skipEmailConfirm?: boolean
}

export type DeleteUserMode = 'now' | 'scheduled'

export interface MigrateUserTasksResult {
	tasksMoved: number
	assigneesMoved: number
}

// Mirrors services/admin/userService.ts against /docsales-admin instead of
// /admin - see pkg/license/license.go for why this fork registers a separate,
// unlicensed route group rather than reuse the gated one.
export default class DocsalesAdminUserService extends AbstractService<IAdminUser> {
	constructor() {
		super({
			getAll: '/docsales-admin/users',
		})
	}

	modelFactory(data: Partial<IAdminUser>) {
		return new AdminUserModel(data)
	}

	async setStatus(id: IAdminUser['id'], status: number) {
		const {data} = await this.http.patch(`/docsales-admin/users/${id}/status`, {status})
		return this.modelUpdateFactory(data)
	}

	async createUser(body: CreateDocsalesAdminUserBody) {
		const {data} = await this.http.post('/docsales-admin/users', body)
		return this.modelCreateFactory(data)
	}

	async deleteUser(id: IAdminUser['id'], mode: DeleteUserMode) {
		await this.http.delete(`/docsales-admin/users/${id}`, {params: {mode}})
	}

	async migrateTasks(fromId: IAdminUser['id'], toId: IAdminUser['id']): Promise<MigrateUserTasksResult> {
		const {data} = await this.http.post(`/docsales-admin/users/${fromId}/migrate-to/${toId}`)
		return {tasksMoved: data.tasks_moved, assigneesMoved: data.assignees_moved}
	}
}
