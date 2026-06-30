import {
  Controller,
  Get,
  Post,
  Patch,
  Delete,
  Param,
  Body,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { UsersService } from './users.service';
import { Roles } from '../auth/roles.decorator';
import { UserRole } from '@violeteyes/shared';
import { CreateUserDto } from './dto/create-user.dto';
import { UpdateUserDto } from './dto/update-user.dto';

/**
 * Users 管理（admin only）。
 *
 * 修复点（ §6.1 高危）：
 *  - 整个 controller 加 @Roles('admin')
 *  - updatePassword 验强度 + 旧密已在 AuthService.changePassword 实现
 */
@Controller('admin/users')
@Roles(UserRole.ADMIN)
export class UsersController {
  constructor(private readonly users: UsersService) {}

  @Get()
  async list() {
    const all = await this.users.list();
    return all.map(UsersService.sanitize);
  }

  @Get(':id')
  async findOne(@Param('id') id: string) {
    const user = await this.users.findById(id);
    return UsersService.sanitize(user);
  }

  @Post()
  @HttpCode(HttpStatus.CREATED)
  async create(@Body() dto: CreateUserDto) {
    const user = await this.users.create(dto);
    return UsersService.sanitize(user);
  }

  @Patch(':id')
  async update(@Param('id') id: string, @Body() dto: UpdateUserDto) {
    const user = await this.users.update(id, dto);
    return UsersService.sanitize(user);
  }

  @Delete(':id')
  @HttpCode(HttpStatus.NO_CONTENT)
  async delete(@Param('id') id: string) {
    await this.users.delete(id);
  }
}