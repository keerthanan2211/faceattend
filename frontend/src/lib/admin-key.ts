// Kept in sessionStorage: it lasts for this browser tab only and is cleared when the tab closes.
const KEY = 'faceattend-admin-key';

export const getAdminKey = () => sessionStorage.getItem(KEY);
export const setAdminKey = (value: string) => sessionStorage.setItem(KEY, value);
export const clearAdminKey = () => sessionStorage.removeItem(KEY);
