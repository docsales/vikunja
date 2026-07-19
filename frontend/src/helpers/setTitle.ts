export function setTitle(title : undefined | string) {
	document.title = (typeof title === 'undefined' || title === '')
		? 'DocSales Tasks'
		: `${title} | DocSales Tasks`
}
