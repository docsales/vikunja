<script setup lang="ts">
import DocSalesLogo from '@/assets/logo-docsales.png'
</script>

<template>
	<div class="docsales-brand">
		<img
			:src="DocSalesLogo"
			alt="DocSales"
			class="logo"
		>
		<span class="app-name">DocSales Tasks Management</span>
	</div>
</template>

<style lang="scss" scoped>
.docsales-brand {
	display: flex;
	align-items: center;
	gap: 0.75rem;
}

.logo {
	inline-size: 48px;
	block-size: 48px;
	border-radius: 10px;
}

.app-name {
	color: var(--logo-text-color);
	font-size: 1.25rem;
	font-weight: 700;
	line-height: 1.2;
}
</style>
