<template>
	<Teleport :to="teleportTarget">
		<Notifications
			position="bottom left"
			:max="2"
			:ignore-duplicates="true"
			class="global-notification"
			role="status"
			aria-live="polite"
		>
			<template #body="{ item, close }">
				<!-- FIXME: overlay whole notification with button and add event listener on that button instead -->
				<div
					class="vue-notification-template vue-notification"
					:class="[
						item.type,
					]"
					@click="close()"
				>
					<div
						v-if="item.title"
						class="notification-title"
					>
						{{ item.title }}
					</div>
					<div class="notification-content">
						<template v-if="Array.isArray(item.text)">
							<template
								v-for="(t, k) in item.text"
								:key="k"
							>
								{{ t }}<br>
							</template>
						</template>
						<template v-else>
							{{ item.text }}
						</template>
						<span
							v-if="item.duplicates > 0"
							class="tw:text-xs tw:font-bold tw:ml-1"
						>
							×{{ item.duplicates + 1 }}
						</span>
					</div>
					<div
						v-if="item.data?.actions?.length > 0"
						class="mbs-2 tw:flex tw:justify-end tw:gap-2"
					>
						<XButton
							v-for="(action, i) in item.data.actions"
							:key="'action_' + i"
							:shadow="false"
							class="is-small"
							variant="secondary"
							@click="action.callback"
						>
							{{ action.title }}
						</XButton>
					</div>
				</div>
			</template>
		</Notifications>
	</Teleport>
</template>

<script lang="ts" setup>
import {onBeforeUnmount, onMounted, ref} from 'vue'

const teleportTarget = ref<string | HTMLElement>('body')
let observer: MutationObserver | null = null

function syncTeleportTarget() {
	const dialogs = document.querySelectorAll<HTMLDialogElement>('dialog.modal-dialog[open]')
	teleportTarget.value = dialogs.item(dialogs.length - 1) ?? 'body'
}

onMounted(() => {
	syncTeleportTarget()
	observer = new MutationObserver(syncTeleportTarget)
	observer.observe(document.body, {
		attributes: true,
		attributeFilter: ['open'],
		childList: true,
		subtree: true,
	})
})

onBeforeUnmount(() => {
	observer?.disconnect()
	observer = null
})
</script>

<style lang="scss" scoped>
.vue-notification {
	z-index: 9999;
}

// This library ships no default stylesheet of its own; the markup above (rendered via
// the #body slot) was previously completely unstyled — success/error feedback had no
// visual distinction at all. Semantic color + a full border/background wash (never a
// side-stripe) + a leading dot on the title, matching the rest of the app's tokens.
.vue-notification-template {
	background: var(--scheme-main);
	color: var(--text);
	border: 1px solid var(--grey-200);
	border-radius: $radius;
	box-shadow: var(--shadow-md);
	padding: .75rem 1rem;
	margin-block-end: .5rem;
	max-inline-size: 22rem;
	cursor: pointer;

	&.success {
		border-color: hsla(var(--success-h), var(--success-s), var(--success-l), 0.35);
		background: hsla(var(--success-h), var(--success-s), var(--success-l), 0.08);

		.notification-title {
			color: var(--success-text);
		}
	}

	&.error {
		border-color: hsla(var(--danger-h), var(--danger-s), var(--danger-l), 0.35);
		background: hsla(var(--danger-h), var(--danger-s), var(--danger-l), 0.08);

		.notification-title {
			color: var(--danger-text);
		}
	}
}

.notification-title {
	display: flex;
	align-items: center;
	gap: .5rem;
	font-weight: 700;
	color: var(--text-strong);

	&::before {
		content: '';
		inline-size: .5rem;
		block-size: .5rem;
		flex-shrink: 0;
		border-radius: 50%;
		background: currentColor;
	}
}

.notification-content {
	margin-block-start: .25rem;
	font-size: .9rem;
	color: var(--text);
}
</style>
