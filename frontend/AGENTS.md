# 规范

## 页面规范



### 新建页面

- 一个页面维度的tsx，必须放在src/pages/页面名称/index.tsx，并且该页面的css样式
需要放在当前页面的文件内的index.css内，组件为components。坚决不需出现home.tsx这种页面tsx
- 如果一个页面包含子页面，则在src/pages/主页面/子页面 新建一个文件夹，
然后这个文件夹里面，有index.tsx、index.css，组件文件夹为components

## 组件规范

- 如果一个组件只有当前页面使用，则放在当前页面的文件夹下的components里面
- 公共组件放在src/components文件夹中