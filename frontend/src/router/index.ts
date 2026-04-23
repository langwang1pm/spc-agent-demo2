/**
 * 路由配置
 */
import { createRouter, createWebHistory } from 'vue-router';
import MainPage from '@/views/MainPage.vue';

const routes = [
  {
    path: '/',
    name: 'Main',
    component: MainPage,
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;