<template>
  <main class="flex-grow">
    <HeroSection />
    <div id="nav-sentinel" class="h-4"></div>
    <CategoryNav />
    <QuickCategories />
    <TimeDeal />
    <ProductList />
    <BrandPromise />
  </main>
</template>

<script setup lang="ts">
import HeroSection from '@/components/sections/HeroSection.vue'
import CategoryNav from '@/components/sections/CategoryNav.vue'
import QuickCategories from '@/components/sections/QuickCategories.vue'
import BrandPromise from '@/components/sections/BrandPromise.vue'
import TimeDeal from '@/components/sections/TimeDeal.vue'
import ProductList from '@/components/sections/ProductList.vue'
</script>


